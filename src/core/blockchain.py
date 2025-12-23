"""
Blockchain implementation for message storage and integrity verification.

This module provides the core blockchain functionality including:
- Block creation with SHA-256 hashing
- Blockchain management and validation
- Simple Proof-of-Work consensus
- Merkle tree for message batching (future)
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Block:
    """A single block in the blockchain."""
    
    index: int
    timestamp: float
    data: dict[str, Any]
    previous_hash: str
    nonce: int = 0
    hash: str = field(default="", init=False)
    
    def __post_init__(self) -> None:
        """Calculate hash after initialization."""
        if not self.hash:
            self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of block contents."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine(self, difficulty: int = 2) -> None:
        """
        Mine the block using Proof-of-Work.
        
        Args:
            difficulty: Number of leading zeros required in hash
        """
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert block to dictionary representation."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        """Create a Block from dictionary representation."""
        block = cls(
            index=data["index"],
            timestamp=data["timestamp"],
            data=data["data"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"]
        )
        block.hash = data["hash"]
        return block


class Blockchain:
    """
    A simple blockchain implementation for message storage.
    
    The blockchain maintains a chain of blocks, each containing
    message data. It provides validation and consensus mechanisms.
    """
    
    def __init__(self, difficulty: int = 2) -> None:
        """
        Initialize the blockchain.
        
        Args:
            difficulty: Mining difficulty (number of leading zeros)
        """
        self.chain: list[Block] = []
        self.pending_data: list[dict[str, Any]] = []
        self.difficulty = difficulty
        
        # Create genesis block
        self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        """Create the first block in the chain."""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={"message": "Genesis Block", "type": "system"},
            previous_hash="0" * 64
        )
        genesis.mine(self.difficulty)
        self.chain.append(genesis)
    
    @property
    def latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_data(self, data: dict[str, Any]) -> None:
        """
        Add data to pending transactions.
        
        Args:
            data: Data to be included in next block
        """
        self.pending_data.append(data)
    
    def mine_pending(self) -> Block | None:
        """
        Mine a new block with all pending data.
        
        Returns:
            The newly mined block, or None if no pending data
        """
        if not self.pending_data:
            return None
        
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data={"messages": self.pending_data.copy()},
            previous_hash=self.latest_block.hash
        )
        new_block.mine(self.difficulty)
        self.chain.append(new_block)
        self.pending_data.clear()
        
        return new_block
    
    def is_chain_valid(self) -> bool:
        """
        Validate the entire blockchain.
        
        Returns:
            True if chain is valid, False otherwise
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            # Verify current block's hash
            if current.hash != current.calculate_hash():
                return False
            
            # Verify link to previous block
            if current.previous_hash != previous.hash:
                return False
            
            # Verify proof of work
            if not current.hash.startswith("0" * self.difficulty):
                return False
        
        return True
    
    def get_messages(self) -> list[dict[str, Any]]:
        """
        Get all messages from the blockchain.
        
        Returns:
            List of all message data in the chain
        """
        messages = []
        for block in self.chain[1:]:  # Skip genesis
            if "messages" in block.data:
                messages.extend(block.data["messages"])
        return messages
    
    def to_dict(self) -> dict[str, Any]:
        """Convert blockchain to dictionary representation."""
        return {
            "difficulty": self.difficulty,
            "chain": [block.to_dict() for block in self.chain],
            "pending_data": self.pending_data
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Blockchain":
        """Create a Blockchain from dictionary representation."""
        blockchain = cls.__new__(cls)
        blockchain.difficulty = data["difficulty"]
        blockchain.chain = [Block.from_dict(b) for b in data["chain"]]
        blockchain.pending_data = data["pending_data"]
        return blockchain
    
    def __len__(self) -> int:
        """Return the length of the chain."""
        return len(self.chain)
    
    def __repr__(self) -> str:
        return f"Blockchain(blocks={len(self.chain)}, pending={len(self.pending_data)})"


def calculate_merkle_root(data_list: list[bytes]) -> str:
    """
    Calculate Merkle root hash for a list of data.
    
    This is used for efficient verification of message batches
    and will be essential for future streaming functionality.
    
    Args:
        data_list: List of data items to hash
        
    Returns:
        Merkle root hash as hex string
    """
    if not data_list:
        return hashlib.sha256(b"").hexdigest()
    
    # Hash each item
    hashes = [hashlib.sha256(data).hexdigest() for data in data_list]
    
    # Build tree
    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])  # Duplicate last hash if odd
        
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        hashes = next_level
    
    return hashes[0]
