"""
Transmission engine for the blockchain messaging protocol.

This module provides:
- TransmissionEngine: Unified interface for sending/receiving data
- Support for text, with extensibility for audio/video
- Automatic chunking for large payloads
- Encryption and signing
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional

from ..core.blockchain import Blockchain
from ..core.crypto import (
    Wallet,
    derive_shared_secret,
    encrypt_message,
    decrypt_message,
    verify_signature,
)
from ..core.message import (
    MessagePayload,
    MessageType,
    ChunkInfo,
    create_text_message,
    create_ack_message,
)
from ..network.p2p import P2PNode
from ..network.peer import Peer
from .chunker import DataChunker, ChunkReassembler, Chunk, CHUNK_SIZE_TEXT

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of content that can be transmitted."""
    
    TEXT = auto()
    BINARY = auto()
    # Future content types
    AUDIO = auto()
    VIDEO = auto()


@dataclass
class ReceivedMessage:
    """A received and decrypted message."""
    
    id: str
    sender: str
    sender_name: Optional[str]
    content: str
    timestamp: float
    verified: bool
    
    def __repr__(self) -> str:
        sender_short = f"{self.sender[:8]}..." if len(self.sender) > 8 else self.sender
        name = f" ({self.sender_name})" if self.sender_name else ""
        return f"Message from {sender_short}{name}: {self.content[:50]}..."


# Type alias for message callback
MessageCallback = Callable[[ReceivedMessage], Coroutine[Any, Any, None]]


class TransmissionEngine:
    """
    Main engine for transmitting and receiving messages.
    
    Provides a high-level interface for:
    - Sending encrypted messages
    - Receiving and decrypting messages
    - Automatic chunking for large data
    - Recording messages to blockchain
    """
    
    def __init__(
        self,
        wallet: Wallet,
        p2p_node: P2PNode,
        blockchain: Optional[Blockchain] = None
    ) -> None:
        """
        Initialize transmission engine.
        
        Args:
            wallet: The user's identity wallet
            p2p_node: P2P networking node
            blockchain: Optional blockchain for message recording
        """
        self.wallet = wallet
        self.p2p_node = p2p_node
        self.blockchain = blockchain or Blockchain(difficulty=2)
        
        # Chunking
        self.chunker = DataChunker(chunk_size=CHUNK_SIZE_TEXT)
        self.reassembler = ChunkReassembler()
        
        # Callbacks
        self._message_callbacks: list[MessageCallback] = []
        
        # Shared secrets cache (peer_id -> secret)
        self._shared_secrets: dict[str, bytes] = {}
        
        # Register P2P message handler
        self.p2p_node.on_message(self._handle_incoming)
    
    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback for received messages."""
        self._message_callbacks.append(callback)
    
    def _get_shared_secret(self, peer: Peer) -> Optional[bytes]:
        """Get or derive shared secret with a peer."""
        if not peer.encryption_key:
            return None
        
        if peer.id not in self._shared_secrets:
            self._shared_secrets[peer.id] = derive_shared_secret(
                self.wallet.encryption_keys.private_key,
                peer.encryption_key
            )
        
        return self._shared_secrets[peer.id]
    
    async def send_text(
        self,
        recipient_id: str,
        text: str,
        encrypt: bool = True
    ) -> bool:
        """
        Send a text message to a peer.
        
        Args:
            recipient_id: Recipient's peer ID (public key hex)
            text: Message text
            encrypt: Whether to encrypt the message
            
        Returns:
            True if sent successfully
        """
        peer = self.p2p_node.get_peer(recipient_id)
        if not peer:
            logger.error(f"Peer not found: {recipient_id[:16]}...")
            return False
        
        content = text.encode()
        nonce = None
        
        # Encrypt if requested and we have peer's encryption key
        if encrypt and peer.encryption_key:
            shared_secret = self._get_shared_secret(peer)
            if shared_secret:
                nonce, content = encrypt_message(content, shared_secret)
        
        # Create and sign message
        message = MessagePayload.create(
            msg_type=MessageType.TEXT,
            sender=self.wallet.address,
            recipient=recipient_id,
            content=content,
            signature=b"",  # Will be set below
            nonce=nonce,
            metadata={"name": self.wallet.name}
        )
        
        # Sign the message
        signable = message.get_signable_content()
        message.signature = self.wallet.sign(signable)
        
        # Record to blockchain
        self.blockchain.add_data({
            "type": "message",
            "id": message.id,
            "sender": message.sender,
            "recipient": message.recipient,
            "timestamp": message.timestamp
        })
        
        # Send via P2P
        success = await self.p2p_node.send_message(message, recipient_id)
        
        if success:
            logger.info(f"Sent message to {peer}")
        
        return success
    
    async def broadcast_text(self, text: str) -> int:
        """
        Broadcast a text message to all connected peers.
        
        Args:
            text: Message text
            
        Returns:
            Number of peers message was sent to
        """
        content = text.encode()
        
        message = MessagePayload.create(
            msg_type=MessageType.TEXT,
            sender=self.wallet.address,
            recipient="*",  # Broadcast
            content=content,
            signature=b"",
            metadata={"name": self.wallet.name}
        )
        
        signable = message.get_signable_content()
        message.signature = self.wallet.sign(signable)
        
        # Record to blockchain
        self.blockchain.add_data({
            "type": "broadcast",
            "id": message.id,
            "sender": message.sender,
            "timestamp": message.timestamp
        })
        
        return await self.p2p_node.broadcast(message)
    
    async def _handle_incoming(
        self,
        message: MessagePayload,
        peer: Peer
    ) -> None:
        """Handle incoming message from P2P layer."""
        
        # Verify signature
        if not peer.public_key:
            logger.warning(f"No public key for peer {peer.id[:16]}...")
            return
        
        signable = message.get_signable_content()
        verified = verify_signature(signable, message.signature, peer.public_key)
        
        if not verified:
            logger.warning(f"Invalid signature from {peer}")
            return
        
        # Handle based on message type
        if message.type == MessageType.TEXT:
            await self._handle_text_message(message, peer, verified)
        
        elif message.type == MessageType.ACK:
            logger.debug(f"Received ACK from {peer}")
        
        elif message.type in (
            MessageType.STREAM_START,
            MessageType.STREAM_CHUNK,
            MessageType.STREAM_END
        ):
            await self._handle_stream_message(message, peer)
    
    async def _handle_text_message(
        self,
        message: MessagePayload,
        peer: Peer,
        verified: bool
    ) -> None:
        """Handle received text message."""
        content = message.content
        
        # Decrypt if encrypted
        if message.nonce and peer.encryption_key:
            shared_secret = self._get_shared_secret(peer)
            if shared_secret:
                try:
                    content = decrypt_message(content, shared_secret, message.nonce)
                except Exception as e:
                    logger.error(f"Failed to decrypt message: {e}")
                    return
        
        # Decode text
        try:
            text = content.decode()
        except UnicodeDecodeError:
            logger.error("Failed to decode message content")
            return
        
        # Create received message
        received = ReceivedMessage(
            id=message.id,
            sender=message.sender,
            sender_name=message.metadata.get("name"),
            content=text,
            timestamp=message.timestamp,
            verified=verified
        )
        
        # Record to blockchain
        self.blockchain.add_data({
            "type": "received",
            "id": message.id,
            "sender": message.sender,
            "timestamp": message.timestamp
        })
        
        # Notify callbacks
        for callback in self._message_callbacks:
            try:
                await callback(received)
            except Exception as e:
                logger.error(f"Message callback error: {e}")
        
        # Send ACK
        ack = create_ack_message(
            sender=self.wallet.address,
            recipient=message.sender,
            original_message_id=message.id,
            sign_func=self.wallet.sign
        )
        await self.p2p_node.send_message(ack, peer.id)
    
    async def _handle_stream_message(
        self,
        message: MessagePayload,
        peer: Peer
    ) -> None:
        """Handle streaming message (for future audio/video)."""
        if not message.chunk_info:
            return
        
        chunk = Chunk(
            stream_id=message.chunk_info.stream_id,
            sequence=message.chunk_info.sequence,
            total=message.chunk_info.total,
            data=message.content
        )
        
        # Add to reassembler
        completed = self.reassembler.add_chunk(chunk)
        
        if completed:
            # Stream complete - process the data
            logger.info(f"Stream {chunk.stream_id} complete: {len(completed)} bytes")
            # Future: Handle completed audio/video stream
    
    def mine_pending(self) -> None:
        """Mine pending blockchain transactions."""
        block = self.blockchain.mine_pending()
        if block:
            logger.info(f"Mined block #{block.index}: {block.hash[:16]}...")
    
    def get_message_history(self) -> list[dict]:
        """Get message history from blockchain."""
        return self.blockchain.get_messages()
