# Blockchain Messaging Protocol (BMP)

A decentralized peer-to-peer messaging protocol built on blockchain principles, designed for secure text transmission with future extensibility for audio/video streaming.

## Features

- 🔐 **End-to-end encryption** using Ed25519 signatures and ChaCha20-Poly1305
- ⛓️ **Blockchain-based message integrity** with merkle tree verification
- 🌐 **P2P network** with WebSocket-based communication
- 📝 **CLI interface** for easy interaction
- 🚀 **Extensible architecture** ready for audio/video streaming

## Installation

```bash
# Clone the repository
cd blockchain-messaging-protocol

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

### Start the Registry Server

```bash
bmp-server --port 8765
```

### Initialize and Register Clients

```bash
# Terminal 1: Client A (Alice)
bmp init --name "Alice"
bmp register --server localhost:8765
bmp listen

# Terminal 2: Client B (Bob)
bmp init --name "Bob"
bmp register --server localhost:8765
bmp send <alice-public-key> "Hello Alice!"
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `bmp init` | Initialize a new wallet/identity |
| `bmp register` | Register with the registry server |
| `bmp send <recipient> <message>` | Send an encrypted message |
| `bmp listen` | Listen for incoming messages |
| `bmp peers` | List known peers |
| `bmp status` | Show connection status |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Client Layer                         │
│  ┌──────────────┐  ┌──────────────────────────────────┐ │
│  │   CLI Tool   │  │     Transmission Engine          │ │
│  └──────────────┘  └──────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    Protocol Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Message    │  │  Cryptography │  │  Serializer  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│                    Network Layer                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          P2P Network (WebSockets)                 │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    Storage Layer                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Blockchain                           │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Development

```bash
# Run tests
pytest tests/ -v

# Run a single test file
pytest tests/test_blockchain.py -v
```

## License

MIT
