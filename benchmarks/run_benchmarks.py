"""
Benchmark suite for Blockchain Messaging Protocol.

Run with: python -m benchmarks.run_benchmarks
"""

import asyncio
import hashlib
import json
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.core.blockchain import Blockchain, Block, calculate_merkle_root
from src.core.crypto import (
    generate_signing_keypair,
    generate_encryption_keypair,
    sign_message,
    verify_signature,
    encrypt_message,
    decrypt_message,
    derive_shared_secret,
)
from src.engine.chunker import DataChunker, ChunkReassembler


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    name: str
    iterations: int
    total_time: float
    times: list[float]
    
    @property
    def avg_time_ms(self) -> float:
        return (self.total_time / self.iterations) * 1000
    
    @property
    def min_time_ms(self) -> float:
        return min(self.times) * 1000
    
    @property
    def max_time_ms(self) -> float:
        return max(self.times) * 1000
    
    @property
    def std_dev_ms(self) -> float:
        return statistics.stdev(self.times) * 1000 if len(self.times) > 1 else 0
    
    @property
    def ops_per_sec(self) -> float:
        return self.iterations / self.total_time
    
    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Iterations: {self.iterations}\n"
            f"  Avg: {self.avg_time_ms:.3f}ms\n"
            f"  Min: {self.min_time_ms:.3f}ms\n"
            f"  Max: {self.max_time_ms:.3f}ms\n"
            f"  Std Dev: {self.std_dev_ms:.3f}ms\n"
            f"  Ops/sec: {self.ops_per_sec:.1f}"
        )


def benchmark(name: str, iterations: int = 1000):
    """Decorator to run a function as a benchmark."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            return BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time=sum(times),
                times=times
            )
        return wrapper
    return decorator


class CryptoBenchmarks:
    """Benchmarks for cryptographic operations."""
    
    def __init__(self):
        self.signing_keys = generate_signing_keypair()
        self.encryption_keys = generate_encryption_keypair()
        self.peer_keys = generate_encryption_keypair()
        self.shared_secret = derive_shared_secret(
            self.encryption_keys.private_key,
            self.peer_keys.public_key
        )
        self.message = b"Hello, World! " * 100  # 1.4KB message
    
    @benchmark("Key Generation (Ed25519)", 1000)
    def bench_keygen_signing(self):
        generate_signing_keypair()
    
    @benchmark("Key Generation (X25519)", 1000)
    def bench_keygen_encryption(self):
        generate_encryption_keypair()
    
    @benchmark("Signing (1.4KB message)", 1000)
    def bench_sign(self):
        sign_message(self.message, self.signing_keys.private_key)
    
    @benchmark("Verification (1.4KB message)", 1000)
    def bench_verify(self):
        signature = sign_message(self.message, self.signing_keys.private_key)
        verify_signature(self.message, signature, self.signing_keys.public_key)
    
    @benchmark("ECDH Key Exchange", 1000)
    def bench_key_exchange(self):
        derive_shared_secret(
            self.encryption_keys.private_key,
            self.peer_keys.public_key
        )
    
    @benchmark("Encryption (1.4KB)", 1000)
    def bench_encrypt(self):
        encrypt_message(self.message, self.shared_secret)
    
    @benchmark("Decryption (1.4KB)", 1000)
    def bench_decrypt(self):
        nonce, ciphertext = encrypt_message(self.message, self.shared_secret)
        decrypt_message(ciphertext, self.shared_secret, nonce)
    
    def run_all(self) -> list[BenchmarkResult]:
        return [
            self.bench_keygen_signing(),
            self.bench_keygen_encryption(),
            self.bench_sign(),
            self.bench_verify(),
            self.bench_key_exchange(),
            self.bench_encrypt(),
            self.bench_decrypt(),
        ]


class BlockchainBenchmarks:
    """Benchmarks for blockchain operations."""
    
    def __init__(self):
        self.blockchain = Blockchain(difficulty=1)
        # Pre-populate with some blocks
        for i in range(10):
            self.blockchain.add_data({"msg": f"message_{i}"})
        self.blockchain.mine_pending()
    
    @benchmark("Add Data to Mempool", 10000)
    def bench_add_data(self):
        bc = Blockchain(difficulty=1)
        bc.add_data({"message": "test", "id": "123"})
    
    @benchmark("Mine Block (difficulty=1)", 100)
    def bench_mine_d1(self):
        bc = Blockchain(difficulty=1)
        for i in range(10):
            bc.add_data({"i": i})
        bc.mine_pending()
    
    @benchmark("Mine Block (difficulty=2)", 50)
    def bench_mine_d2(self):
        bc = Blockchain(difficulty=2)
        for i in range(10):
            bc.add_data({"i": i})
        bc.mine_pending()
    
    @benchmark("Chain Validation (10 blocks)", 1000)
    def bench_validate(self):
        bc = Blockchain(difficulty=1)
        for i in range(10):
            bc.add_data({"i": i})
            bc.mine_pending()
        bc.is_chain_valid()
    
    @benchmark("Block Lookup by Hash", 10000)
    def bench_lookup_hash(self):
        self.blockchain.get_block_by_hash(self.blockchain.latest_block.hash)
    
    @benchmark("Block Lookup by Height", 10000)
    def bench_lookup_height(self):
        self.blockchain.get_block_by_height(1)
    
    @benchmark("Merkle Root (100 items)", 1000)
    def bench_merkle_root(self):
        data = [f"item_{i}".encode() for i in range(100)]
        calculate_merkle_root(data)
    
    @benchmark("Save to Disk", 100)
    def bench_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "blockchain.json"
            self.blockchain.save(path)
    
    @benchmark("Load from Disk", 100)
    def bench_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "blockchain.json"
            self.blockchain.save(path)
            Blockchain.load(path)
    
    def run_all(self) -> list[BenchmarkResult]:
        return [
            self.bench_add_data(),
            self.bench_mine_d1(),
            self.bench_mine_d2(),
            self.bench_validate(),
            self.bench_lookup_hash(),
            self.bench_lookup_height(),
            self.bench_merkle_root(),
            self.bench_save(),
            self.bench_load(),
        ]


class ChunkerBenchmarks:
    """Benchmarks for data chunking."""
    
    def __init__(self):
        self.small_data = b"x" * 1024          # 1KB
        self.medium_data = b"x" * (64 * 1024)  # 64KB
        self.large_data = b"x" * (1024 * 1024) # 1MB
    
    @benchmark("Chunk 1KB data", 10000)
    def bench_chunk_1kb(self):
        chunker = DataChunker(chunk_size=256)
        list(chunker.chunk(self.small_data))
    
    @benchmark("Chunk 64KB data", 1000)
    def bench_chunk_64kb(self):
        chunker = DataChunker(chunk_size=1024)
        list(chunker.chunk(self.medium_data))
    
    @benchmark("Chunk 1MB data", 100)
    def bench_chunk_1mb(self):
        chunker = DataChunker(chunk_size=64 * 1024)
        list(chunker.chunk(self.large_data))
    
    @benchmark("Reassemble 64KB (64 chunks)", 1000)
    def bench_reassemble(self):
        chunker = DataChunker(chunk_size=1024)
        chunks = list(chunker.chunk(self.medium_data))
        
        reassembler = ChunkReassembler()
        for chunk in chunks:
            reassembler.add_chunk(chunk)
    
    def run_all(self) -> list[BenchmarkResult]:
        return [
            self.bench_chunk_1kb(),
            self.bench_chunk_64kb(),
            self.bench_chunk_1mb(),
            self.bench_reassemble(),
        ]


def run_all_benchmarks():
    """Run all benchmarks and print results."""
    print("=" * 60)
    print("BLOCKCHAIN MESSAGING PROTOCOL - BENCHMARK SUITE")
    print("=" * 60)
    print()
    
    all_results = []
    
    # Crypto benchmarks
    print("🔐 CRYPTOGRAPHY BENCHMARKS")
    print("-" * 40)
    crypto = CryptoBenchmarks()
    for result in crypto.run_all():
        print(result)
        print()
        all_results.append(result)
    
    # Blockchain benchmarks
    print("⛓️ BLOCKCHAIN BENCHMARKS")
    print("-" * 40)
    blockchain = BlockchainBenchmarks()
    for result in blockchain.run_all():
        print(result)
        print()
        all_results.append(result)
    
    # Chunker benchmarks
    print("📦 CHUNKING BENCHMARKS")
    print("-" * 40)
    chunker = ChunkerBenchmarks()
    for result in chunker.run_all():
        print(result)
        print()
        all_results.append(result)
    
    # Summary table
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Benchmark':<40} {'Avg (ms)':<12} {'Ops/sec':<12}")
    print("-" * 64)
    for r in all_results:
        print(f"{r.name:<40} {r.avg_time_ms:<12.3f} {r.ops_per_sec:<12.1f}")
    
    return all_results


if __name__ == "__main__":
    run_all_benchmarks()
