# Performance Benchmarks

## Test Environment

- **CPU**: Apple Silicon / Intel (varies)
- **Python**: 3.11+
- **Date**: December 2024

## Cryptography Performance

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| **Key Gen (Ed25519)** | 0.065ms | 15,270 | Signing key pair |
| **Key Gen (X25519)** | 0.071ms | 14,137 | Encryption key pair |
| **Signing (1.4KB)** | 0.126ms | 7,917 | Ed25519 signature |
| **Verification (1.4KB)** | 0.268ms | 3,733 | Ed25519 verify |
| **ECDH Key Exchange** | 0.191ms | 5,234 | X25519 shared secret |
| **Encryption (1.4KB)** | 0.003ms | 311,709 | ChaCha20-Poly1305 |
| **Decryption (1.4KB)** | 0.005ms | 195,595 | ChaCha20-Poly1305 |

### Key Insights

- **Encryption is extremely fast** - 300K+ ops/sec makes real-time messaging trivial
- **Verification is slower than signing** - 2x slower, but still fast enough for high throughput
- **Key exchange is a one-time cost** - 0.19ms per new peer connection

## Blockchain Performance

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| **Add to Mempool** | 0.047ms | 21,340 | Add pending data |
| **Mine (difficulty=1)** | 0.153ms | 6,527 | Fast for testing |
| **Mine (difficulty=2)** | 1.832ms | 546 | Production setting |
| **Chain Validation** | 0.586ms | 1,708 | 10 blocks |
| **Block Lookup (hash)** | <0.001ms | 9,259,028 | O(1) indexed |
| **Block Lookup (height)** | <0.001ms | 12,366,364 | O(1) indexed |
| **Merkle Root (100 items)** | 0.062ms | 16,192 | SHA-256 tree |
| **Save to Disk** | 0.290ms | 3,447 | Atomic write |
| **Load from Disk** | 0.331ms | 3,018 | With index rebuild |

### Key Insights

- **Block lookups are instant** - 9M+ ops/sec thanks to O(1) indexing
- **Mining scales with difficulty** - 3x increase from d=1 to d=2
- **Persistence is fast** - Full save/load cycle under 1ms

## Chunking Performance

| Operation | Avg Time | Ops/sec | Data Size |
|-----------|----------|---------|-----------|
| **Chunk 1KB** | 0.005ms | 206,483 | 1KB |
| **Chunk 64KB** | 0.056ms | 17,745 | 64KB |
| **Chunk 1MB** | 0.345ms | 2,898 | 1MB |
| **Reassemble 64KB** | 0.102ms | 9,776 | 64 chunks |

### Key Insights

- **Linear scaling** - Chunking time ~linear with data size
- **Reassembly overhead** - ~2x chunking time for reassembly

## Throughput Estimates

Based on benchmarks, here are theoretical throughput limits:

### Messages per Second

| Scenario | Messages/sec | Bottleneck |
|----------|--------------|------------|
| Sign + Encrypt (1KB) | ~5,000 | Signature generation |
| Verify + Decrypt (1KB) | ~3,000 | Signature verification |
| Full roundtrip (1KB) | ~1,500 | Combined |

### File Transfer

| File Size | Chunk Size | Chunks | Total Time |
|-----------|------------|--------|------------|
| 1MB | 64KB | 16 | ~5ms + network |
| 100MB | 1MB | 100 | ~35ms + network |
| 1GB | 1MB | 1,024 | ~350ms + network |

## Running Benchmarks

```bash
# Run full benchmark suite
python -m benchmarks.run_benchmarks

# Run specific category
python -c "from benchmarks.run_benchmarks import CryptoBenchmarks; c = CryptoBenchmarks(); print(c.run_all())"
```

## Comparison with Other Systems

| System | Sign Time | Encrypt Time | Notes |
|--------|-----------|--------------|-------|
| **BMP** | 0.126ms | 0.003ms | Ed25519 + ChaCha20 |
| Signal Protocol | ~0.1ms | ~0.05ms | X3DH + Double Ratchet |
| GPG (RSA-4096) | ~10ms | ~1ms | Legacy system |

BMP achieves comparable performance to Signal Protocol while maintaining a simpler architecture suitable for blockchain integration.
