# Blockchain Messaging Protocol (BMP)

> A Decentralized Peer-to-Peer Secure Messaging Framework Built on Distributed Ledger Technology

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Abstract

This project presents a novel approach to secure messaging by integrating blockchain technology with peer-to-peer (P2P) communication protocols. The Blockchain Messaging Protocol (BMP) addresses key challenges in decentralized communication systems: **message integrity**, **non-repudiation**, **end-to-end encryption**, and **resistance to censorship**. Unlike traditional centralized messaging platforms, BMP eliminates single points of failure while maintaining cryptographic guarantees through distributed ledger technology.

The architecture is designed with extensibility in mind, supporting future integration of real-time audio and video streaming protocols, making it suitable for building comprehensive decentralized communication platforms.

---

## Table of Contents

- [Introduction](#introduction)
- [Related Work](#related-work)
- [System Architecture](#system-architecture)
- [Cryptographic Design](#cryptographic-design)
- [Protocol Specification](#protocol-specification)
- [Scalability Considerations](#scalability-considerations)
- [Installation](#installation)
- [Usage](#usage)
- [Evaluation](#evaluation)
- [Future Work](#future-work)
- [References](#references)

---

## Introduction

### Problem Statement

Centralized messaging platforms present several fundamental challenges:

1. **Single Point of Failure**: Server outages can disrupt communication for millions of users [1]
2. **Privacy Concerns**: Centralized storage creates attractive targets for data breaches [2]
3. **Censorship Vulnerability**: Central authorities can restrict or monitor communications [3]
4. **Trust Requirements**: Users must trust platform operators with their metadata and, in some cases, message content [4]

### Our Contribution

BMP addresses these challenges by:

- **Decentralizing message routing** through a P2P gossip protocol based on libp2p design principles [5]
- **Ensuring message integrity** via blockchain-based immutable logging with Merkle tree verification [6]
- **Providing end-to-end encryption** using modern elliptic curve cryptography (Ed25519/X25519) [7]
- **Enabling non-repudiation** through digital signatures on all transmitted messages [8]

---

## Related Work

### Blockchain-Based Messaging Systems

Several prior works have explored blockchain for secure messaging:

| System | Consensus | Encryption | Scalability | 
|--------|-----------|------------|-------------|
| Bitmessage [9] | PoW | ECIES | Limited (all nodes store all messages) |
| Session [10] | Service Nodes | Signal Protocol | Onion routing for metadata protection |
| Status.im [11] | Ethereum | Whisper Protocol | Smart contract integration |
| **BMP (Ours)** | Lightweight PoW | Ed25519 + ChaCha20-Poly1305 | Chunked streaming, extensible |

### Key Exchange Protocols

Our implementation leverages the **X25519 Elliptic Curve Diffie-Hellman (ECDH)** key exchange, which provides 128-bit security with efficient 32-byte keys [12]. This approach, formalized by Bernstein [13], offers significant performance advantages over traditional RSA-based key exchange while maintaining equivalent security guarantees.

### Message Authentication

We employ **Ed25519** digital signatures [14], which provide:
- 128-bit security level
- Small signature size (64 bytes)
- Fast signing and verification (suitable for high-throughput messaging)
- Deterministic signatures (same message + key = same signature)

---

## System Architecture

### High-Level Component Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[CLI Client]
        TxEngine[Transmission Engine]
    end
    
    subgraph "Protocol Layer"
        MP[Message Protocol]
        Crypto[Cryptography]
        Serializer[Serializer]
    end
    
    subgraph "Network Layer"
        P2P[P2P Network]
        DHT[Peer Discovery/DHT]
    end
    
    subgraph "Storage Layer"
        BC[Blockchain]
        Blocks[Blocks]
    end
    
    subgraph "Server"
        Registry[Registry Server]
        Bootstrap[Bootstrap Node]
    end
    
    CLI --> TxEngine
    TxEngine --> MP
    MP --> Crypto
    MP --> Serializer
    TxEngine --> P2P
    P2P --> DHT
    P2P --> Registry
    P2P --> BC
    BC --> Blocks
    Registry --> Bootstrap
```

### Layer Descriptions

| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Client** | CLI, Transmission Engine | User interface, message orchestration |
| **Protocol** | Message Protocol, Crypto, Serializer | Message formatting, encryption, serialization |
| **Network** | P2P Network, DHT | Peer discovery, message routing |
| **Storage** | Blockchain | Message integrity, ordering, non-repudiation |
| **Server** | Registry, Bootstrap | Initial peer discovery, network bootstrapping |

### Message Transmission Flow

The following sequence diagram illustrates the complete lifecycle of a message from sender to recipient:

```mermaid
sequenceDiagram
    participant A as Client A
    participant E as Tx Engine
    participant BC as Blockchain
    participant P2P as P2P Network
    participant B as Client B

    A->>E: send(recipient, message)
    E->>E: Encrypt with B's public key
    E->>E: Sign with A's private key
    E->>E: Create MessagePayload
    E->>BC: Add to pending block
    E->>P2P: Broadcast to network
    P2P->>B: Deliver message
    B->>B: Verify signature
    B->>B: Decrypt message
    B->>A: Send ACK
```

### Client Registration Flow

New clients bootstrap into the network through a registry server:

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Registry
    participant N as P2P Network

    C->>C: Generate key pair
    C->>R: Register(public_key, address)
    R->>R: Store mapping
    R->>C: Return peer list
    C->>N: Connect to peers
    N->>C: Exchange peer info
```

---

## Cryptographic Design

### Key Hierarchy

Each user wallet contains two key pairs, following the principle of key separation [15]:

```
Wallet
├── Signing Keys (Ed25519)
│   ├── Private Key (32 bytes)
│   └── Public Key (32 bytes) → User Address
│
└── Encryption Keys (X25519)
    ├── Private Key (32 bytes)
    └── Public Key (32 bytes) → Encryption Endpoint
```

### Encryption Scheme

Message encryption follows the **Encrypt-then-Sign** paradigm, recommended for authenticated encryption in asynchronous protocols [16]:

1. **Key Derivation**: Shared secret via X25519 ECDH + HKDF-SHA256 [17]
2. **Symmetric Encryption**: ChaCha20-Poly1305 AEAD [18]
3. **Digital Signature**: Ed25519 over the encrypted payload

```
ciphertext = ChaCha20-Poly1305(shared_secret, nonce, plaintext)
signature = Ed25519.Sign(private_key, H(metadata || ciphertext))
```

### Security Properties

| Property | Mechanism | Reference |
|----------|-----------|-----------|
| Confidentiality | ChaCha20-Poly1305 | Bernstein [18] |
| Integrity | Poly1305 MAC | Bernstein [18] |
| Authentication | Ed25519 signatures | Bernstein et al. [14] |
| Forward Secrecy | Ephemeral X25519 (future) | Signal Protocol [19] |
| Non-repudiation | Blockchain logging | Nakamoto [6] |

---

## Protocol Specification

### Message Payload Structure

```python
@dataclass
class MessagePayload:
    id: str              # UUIDv4 message identifier
    type: MessageType    # TEXT, ACK, STREAM_*, etc.
    sender: str          # Ed25519 public key (hex)
    recipient: str       # Ed25519 public key (hex) or "*" for broadcast
    timestamp: float     # Unix timestamp
    content: bytes       # Encrypted message content
    signature: bytes     # Ed25519 signature (64 bytes)
    nonce: bytes         # ChaCha20-Poly1305 nonce (12 bytes)
    chunk_info: ChunkInfo  # Optional, for streaming
```

### Message Types

| Type | Code | Description |
|------|------|-------------|
| `TEXT` | 0x01 | Standard text message |
| `ACK` | 0x02 | Acknowledgment |
| `STREAM_START` | 0x03 | Begin streaming session |
| `STREAM_CHUNK` | 0x04 | Streaming data chunk |
| `STREAM_END` | 0x05 | End streaming session |

### Wire Protocol

The wire protocol uses a custom framing format over WebSocket:

```
┌─────────────┬──────────┬──────────────┬─────────────┐
│ Magic (4B)  │ Type(1B) │ Length (4B)  │ Payload     │
├─────────────┼──────────┼──────────────┼─────────────┤
│ "BMP\x01"   │ FrameType│ Big-endian   │ Variable    │
└─────────────┴──────────┴──────────────┴─────────────┘
```

---

## Scalability Considerations

### Current vs. Future Capabilities

The architecture is designed with media streaming extensibility:

| Feature | Text (Current) | Audio/Video (Future) |
|---------|----------------|---------------------|
| Chunk Size | 64 KB | 1-4 MB |
| Transport | Reliable (WebSocket) | Reliable + Unreliable (WebRTC) |
| Encoding | UTF-8/Binary | Opus/VP9/AV1 [20] |
| Latency | Best-effort | Real-time priority |
| Delivery | Store-and-forward | Streaming |

### Extension Points

1. **`MessageType.STREAM_*`**: Pre-defined message types for streaming
2. **`ChunkInfo`**: Sequence numbers and hashes for chunk reassembly
3. **Codec Registry**: Pluggable encoder/decoder system in TransmissionEngine
4. **QoS Layer**: Priority queuing can be added to P2P module

### Blockchain Scalability

For high-throughput messaging scenarios, the blockchain design incorporates:

- **Merkle Tree Batching**: Multiple messages per block [6]
- **Lightweight Consensus**: Reduced PoW difficulty (configurable)
- **Local Chain**: Each node maintains message history locally (no global consensus required)
- **Pruning**: Historical blocks can be archived (future work)

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone https://github.com/nileshchakraborty/blockchain-messaging-protocol.git
cd blockchain-messaging-protocol

# Install with development dependencies
pip install -e ".[dev]"
```

---

## Usage

### Start the Registry Server

```bash
bmp-server --port 8765
```

### Initialize and Register Clients

```bash
# Terminal 1: Client A (Alice)
bmp init --name "Alice"
bmp register --server localhost:8765
bmp listen --port 8766

# Terminal 2: Client B (Bob)
bmp init --name "Bob"
bmp register --server localhost:8765
bmp send --port 8767 <alice-public-key> "Hello Alice!"
```

> **Note**: When running multiple clients on the same machine, use different `--port` values to avoid conflicts.

### Development Mode

When developing, you can run commands directly via Python modules:

```bash
# Server
python -m src.server.server --port 8765 --debug

# Client (use --data-dir for separate client identities)
python -m src.client.cli --data-dir /tmp/alice init --name "Alice"
python -m src.client.cli --data-dir /tmp/alice listen --port 8766
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `bmp init --name <name>` | Initialize a new wallet/identity |
| `bmp register --server <host:port>` | Register with the registry server |
| `bmp send [--port <port>] <recipient> <message>` | Send an encrypted message |
| `bmp send-file [--port <port>] <recipient> <file>` | Send an encrypted file |
| `bmp listen [--port <port>]` | Listen for incoming messages and files |
| `bmp peers` | List known peers |
| `bmp status` | Show connection status |
| `bmp history` | Show message and file transfer history |

### File Transfer

Send files (images, documents, audio, video) with end-to-end encryption:

```bash
# Send a file to a peer
bmp send-file --port 8768 <recipient-address> ./photo.jpg

# Files are automatically:
# - Validated (size limits, MIME type detection)
# - Chunked for efficient transfer (256KB-1MB chunks)
# - Encrypted with ChaCha20-Poly1305
# - Hash-verified on receipt (SHA-256)
# - Saved to ~/.bmp/downloads/
```

**Supported file types:**
- **Images**: jpg, png, gif, webp (max 50MB)
- **Audio**: mp3, wav, ogg, flac (max 200MB)
- **Video**: mp4, webm, mov (max 2GB)
- **Documents**: pdf, txt, doc, zip (max 100MB)

---

## Evaluation

### Test Suite

```bash
# Run all tests (90 tests)
pytest tests/ -v

# Run specific test modules
pytest tests/test_crypto.py -v      # Cryptographic primitives
pytest tests/test_blockchain.py -v  # Blockchain operations
pytest tests/test_integration.py -v # End-to-end scenarios
pytest tests/test_media.py -v       # File transfer & media handling
```

### Security Considerations

| Threat | Mitigation |
|--------|------------|
| Man-in-the-Middle | End-to-end encryption with authenticated key exchange |
| Replay Attacks | Message IDs + timestamps + blockchain ordering |
| Impersonation | Ed25519 digital signatures |
| Message Tampering | Poly1305 MAC + blockchain immutability |
| Metadata Analysis | Future: onion routing integration |

---

## Future Work

1. **Double Ratchet Protocol**: Implement Signal's double ratchet for perfect forward secrecy [19]
2. **Onion Routing**: Integrate Tor-style routing for metadata protection [21]
3. **WebRTC Integration**: Enable real-time audio/video with existing infrastructure [22]
4. **Decentralized Identity**: Replace registry with DID-based discovery [23]
5. **Mobile Clients**: iOS/Android applications with background message sync
6. **Formal Verification**: Prove security properties using ProVerif or Tamarin [24]

---

## Directory Structure

```
blockchain-messaging-protocol/
├── src/
│   ├── core/           # Blockchain, cryptography, message protocol
│   ├── network/        # P2P networking, peer management
│   ├── server/         # Registry server
│   ├── client/         # CLI client
│   └── engine/         # Transmission engine, chunking
├── tests/              # Test suite
├── pyproject.toml      # Project configuration
└── README.md           # This file
```

---

## References

[1] A. Acquisti and R. Gross, "Imagined Communities: Awareness, Information Sharing, and Privacy on the Facebook," *Privacy Enhancing Technologies*, 2006.

[2] R. Dingledine, N. Mathewson, and P. Syverson, "Tor: The Second-Generation Onion Router," *USENIX Security Symposium*, 2004.

[3] S. Burnett and N. Feamster, "Encore: Lightweight Measurement of Web Censorship with Cross-Origin Requests," *ACM SIGCOMM*, 2015.

[4] K. Ermoshina, F. Musiani, and H. Halpin, "End-to-End Encrypted Messaging Protocols: An Overview," *F. Bagnoli et al. (eds.), INSCI 2016*, LNCS, vol. 9934, 2016.

[5] Protocol Labs, "libp2p: A Modular Network Stack," https://libp2p.io/, 2023.

[6] S. Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System," 2008.

[7] D. J. Bernstein and T. Lange, "SafeCurves: Choosing Safe Curves for Elliptic-Curve Cryptography," https://safecurves.cr.yp.to/, 2014.

[8] A. J. Menezes, P. C. van Oorschot, and S. A. Vanstone, *Handbook of Applied Cryptography*, CRC Press, 1996.

[9] J. Warren, "Bitmessage: A Peer-to-Peer Message Authentication and Delivery System," 2012.

[10] Loki Foundation, "Session: A Model for End-to-End Encrypted Conversations with Minimal Metadata Leakage," *Whitepaper*, 2020.

[11] Status.im, "Status: A Mobile Ethereum OS," https://status.im/whitepaper.pdf, 2017.

[12] D. J. Bernstein, "Curve25519: New Diffie-Hellman Speed Records," *Public Key Cryptography – PKC 2006*, LNCS, vol. 3958, 2006.

[13] D. J. Bernstein, "A State-of-the-Art Diffie-Hellman Function," https://cr.yp.to/ecdh.html, 2006.

[14] D. J. Bernstein, N. Duif, T. Lange, P. Schwabe, and B.-Y. Yang, "High-Speed High-Security Signatures," *Journal of Cryptographic Engineering*, vol. 2, no. 2, pp. 77-89, 2012.

[15] C. Boyd and A. Mathuria, *Protocols for Authentication and Key Establishment*, Springer, 2003.

[16] H. Krawczyk, "The Order of Encryption and Authentication for Protecting Communications (Or: How Secure Is SSL?)," *CRYPTO 2001*, LNCS, vol. 2139, 2001.

[17] H. Krawczyk and P. Eronen, "HMAC-based Extract-and-Expand Key Derivation Function (HKDF)," RFC 5869, 2010.

[18] D. J. Bernstein, "ChaCha, a Variant of Salsa20," *SASC 2008*, 2008.

[19] M. Marlinspike and T. Perrin, "The Double Ratchet Algorithm," *Signal Specifications*, 2016.

[20] J. Bankoski et al., "VP9 Bitstream & Decoding Process Specification," *Google*, 2016.

[21] R. Dingledine, N. Mathewson, and P. Syverson, "Tor: The Second-Generation Onion Router," *USENIX Security*, 2004.

[22] A. Johnston and D. Burnett, *WebRTC: APIs and RTCWEB Protocols of the HTML5 Real-Time Web*, Digital Codex LLC, 2014.

[23] W3C, "Decentralized Identifiers (DIDs) v1.0," https://www.w3.org/TR/did-core/, 2022.

[24] B. Blanchet, "Modeling and Verifying Security Protocols with the Applied Pi Calculus and ProVerif," *Foundations and Trends in Privacy and Security*, vol. 1, no. 1–2, 2016.

---

## License

MIT License

## Authors

- Nilesh Chakraborty

## Acknowledgments

This work builds upon foundational research in distributed systems, cryptography, and blockchain technology. We acknowledge the contributions of the open-source community, particularly the developers of the `cryptography`, `websockets`, and `click` Python libraries.
