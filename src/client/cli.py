"""
Command-line interface for the blockchain messaging protocol client.

Usage:
    bmp init --name "Alice"
    bmp register --server localhost:8765
    bmp send <recipient> "Hello!"
    bmp listen
    bmp peers
    bmp status
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from .client import Client, ClientConfig
from ..engine.engine import ReceivedMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)

# Global client instance
_client: Optional[Client] = None


def get_client() -> Client:
    """Get or create client instance."""
    global _client
    if _client is None:
        _client = Client()
    return _client


def print_banner():
    """Print the BMP banner."""
    click.echo(click.style("""
╔═══════════════════════════════════════════════╗
║   Blockchain Messaging Protocol (BMP) Client  ║
╚═══════════════════════════════════════════════╝
    """, fg="cyan", bold=True))


@click.group()
@click.option("--data-dir", type=click.Path(), help="Data directory path")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, data_dir: Optional[str], debug: bool):
    """Blockchain Messaging Protocol - Secure P2P Messaging"""
    ctx.ensure_object(dict)
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    config = ClientConfig()
    if data_dir:
        config.data_dir = Path(data_dir)
    
    ctx.obj["config"] = config


@cli.command()
@click.option("--name", "-n", required=True, help="Your display name")
@click.pass_context
def init(ctx, name: str):
    """Initialize a new wallet/identity."""
    print_banner()
    
    config = ctx.obj["config"]
    client = Client(config)
    
    if client.wallet_path.exists():
        if not click.confirm("Wallet already exists. Overwrite?"):
            return
        client.wallet_path.unlink()
    
    try:
        wallet = client.init_wallet(name)
        
        click.echo()
        click.echo(click.style("✓ Wallet created successfully!", fg="green", bold=True))
        click.echo()
        click.echo(f"  Name:    {wallet.name}")
        click.echo(f"  Address: {click.style(wallet.address, fg='yellow')}")
        click.echo()
        click.echo(click.style("⚠ Keep your wallet file safe:", fg="yellow"))
        click.echo(f"  {client.wallet_path}")
        click.echo()
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option("--server", "-s", default="localhost:8765", help="Registry server address")
@click.pass_context
def register(ctx, server: str):
    """Register with the registry server."""
    print_banner()
    
    config = ctx.obj["config"]
    
    # Parse server address
    if ":" in server:
        host, port = server.rsplit(":", 1)
        config.registry_host = host
        config.registry_port = int(port)
    else:
        config.registry_host = server
    
    client = Client(config)
    
    if not client.load_wallet():
        click.echo(click.style("✗ No wallet found. Run 'bmp init' first.", fg="red"))
        sys.exit(1)
    
    click.echo(f"Registering as {client.wallet.name}...")
    click.echo(f"Server: {config.registry_host}:{config.registry_port}")
    
    async def do_register():
        success = await client.register()
        return success, client.get_peers()
    
    try:
        success, peers = asyncio.run(do_register())
        
        if success:
            click.echo()
            click.echo(click.style("✓ Registration successful!", fg="green", bold=True))
            click.echo()
            
            if peers:
                click.echo(f"Known peers ({len(peers)}):")
                for peer in peers:
                    name = peer.get("name", "Unknown")
                    peer_id = peer["peer_id"]
                    click.echo(f"  • {name}: {peer_id[:16]}...")
            else:
                click.echo("No other peers registered yet.")
            
            click.echo()
        else:
            click.echo(click.style("✗ Registration failed", fg="red"))
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.argument("recipient")
@click.argument("message")
@click.option("--server", "-s", default="localhost:8765", help="Registry server address")
@click.option("--port", "-p", default=8766, help="P2P port to use")
@click.pass_context
def send(ctx, recipient: str, message: str, server: str, port: int):
    """Send a message to a peer."""
    config = ctx.obj["config"]
    config.p2p_port = port
    
    # Parse server address
    if ":" in server:
        host, port_str = server.rsplit(":", 1)
        config.registry_host = host
        config.registry_port = int(port_str)
    else:
        config.registry_host = server
    
    client = Client(config)
    
    if not client.load_wallet():
        click.echo(click.style("✗ No wallet found. Run 'bmp init' first.", fg="red"))
        sys.exit(1)
    
    async def do_send():
        # Register first to get peer list
        if not await client.register():
            return False
        
        # Start client
        await client.start()
        
        # Find recipient
        full_recipient = recipient
        if len(recipient) < 64:
            # Try to find by partial ID
            for peer in client.get_peers():
                if peer["peer_id"].startswith(recipient):
                    full_recipient = peer["peer_id"]
                    break
        
        # Send message
        success = await client.send_message(full_recipient, message)
        
        await client.stop()
        return success
    
    try:
        click.echo(f"Sending message to {recipient[:16]}...")
        
        success = asyncio.run(do_send())
        
        if success:
            click.echo(click.style("✓ Message sent!", fg="green"))
        else:
            click.echo(click.style("✗ Failed to send message", fg="red"))
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option("--server", "-s", default="localhost:8765", help="Registry server address")
@click.option("--port", "-p", default=8766, help="P2P port to listen on")
@click.pass_context
def listen(ctx, server: str, port: int):
    """Listen for incoming messages."""
    print_banner()
    
    config = ctx.obj["config"]
    config.p2p_port = port
    
    # Parse server address
    if ":" in server:
        host, port_str = server.rsplit(":", 1)
        config.registry_host = host
        config.registry_port = int(port_str)
    else:
        config.registry_host = server
    
    client = Client(config)
    
    if not client.load_wallet():
        click.echo(click.style("✗ No wallet found. Run 'bmp init' first.", fg="red"))
        sys.exit(1)
    
    async def handle_message(msg: ReceivedMessage):
        """Display received message."""
        timestamp = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S")
        sender = msg.sender_name or msg.sender[:16] + "..."
        verified = "✓" if msg.verified else "✗"
        
        click.echo()
        click.echo(click.style(f"[{timestamp}] ", fg="blue") + 
                   click.style(f"{sender}", fg="yellow", bold=True) +
                   click.style(f" [{verified}]", fg="green" if msg.verified else "red"))
        click.echo(f"  {msg.content}")
    
    async def run_listener():
        # Register
        click.echo(f"Connecting to registry at {config.registry_host}:{config.registry_port}...")
        
        if not await client.register():
            click.echo(click.style("✗ Registration failed", fg="red"))
            return
        
        click.echo(click.style("✓ Registered", fg="green"))
        
        # Start client
        await client.start()
        client.on_message(handle_message)
        
        click.echo()
        click.echo(click.style("Listening for messages...", fg="cyan", bold=True))
        click.echo(click.style("Press Ctrl+C to stop", fg="bright_black"))
        click.echo()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        
        await client.stop()
    
    try:
        asyncio.run(run_listener())
    except KeyboardInterrupt:
        click.echo()
        click.echo("Stopped.")


@cli.command()
@click.option("--server", "-s", default="localhost:8765", help="Registry server address")
@click.pass_context
def peers(ctx, server: str):
    """List known peers."""
    config = ctx.obj["config"]
    
    # Parse server address
    if ":" in server:
        host, port = server.rsplit(":", 1)
        config.registry_host = host
        config.registry_port = int(port)
    else:
        config.registry_host = server
    
    client = Client(config)
    
    if not client.load_wallet():
        click.echo(click.style("✗ No wallet found. Run 'bmp init' first.", fg="red"))
        sys.exit(1)
    
    async def get_peers():
        if not await client.register():
            return []
        return client.get_peers()
    
    try:
        peer_list = asyncio.run(get_peers())
        
        click.echo()
        if peer_list:
            click.echo(click.style(f"Known Peers ({len(peer_list)})", fg="cyan", bold=True))
            click.echo()
            
            for peer in peer_list:
                name = peer.get("name", "Unknown")
                peer_id = peer["peer_id"]
                address = f"{peer['address']}:{peer['port']}"
                
                click.echo(f"  {click.style(name, fg='yellow', bold=True)}")
                click.echo(f"    ID:      {peer_id[:32]}...")
                click.echo(f"    Address: {address}")
                click.echo()
        else:
            click.echo("No peers found.")
            
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show client status."""
    print_banner()
    
    config = ctx.obj["config"]
    client = Client(config)
    
    click.echo(click.style("Status", fg="cyan", bold=True))
    click.echo()
    
    if client.load_wallet():
        wallet = client.wallet
        click.echo(f"  Wallet:     {click.style('✓ Initialized', fg='green')}")
        click.echo(f"  Name:       {wallet.name}")
        click.echo(f"  Address:    {wallet.address_short}")
        click.echo(f"  Full ID:    {wallet.address}")
    else:
        click.echo(f"  Wallet:     {click.style('✗ Not initialized', fg='red')}")
    
    click.echo()
    click.echo(f"  Data dir:   {config.data_dir}")
    click.echo(f"  P2P port:   {config.p2p_port}")
    click.echo(f"  Registry:   {config.registry_host}:{config.registry_port}")
    
    # Check blockchain
    if client.load_blockchain():
        bc = client.blockchain
        click.echo()
        click.echo(f"  Blockchain: {len(bc)} blocks")
    
    click.echo()


@cli.command()
@click.pass_context  
def history(ctx):
    """Show message history from blockchain."""
    config = ctx.obj["config"]
    client = Client(config)
    
    if not client.load_wallet():
        click.echo(click.style("✗ No wallet found.", fg="red"))
        sys.exit(1)
    
    client.load_blockchain()
    
    messages = client.blockchain.get_messages() if client.blockchain else []
    
    click.echo()
    if messages:
        click.echo(click.style(f"Message History ({len(messages)} records)", fg="cyan", bold=True))
        click.echo()
        
        for msg in messages[-20:]:  # Show last 20
            msg_type = msg.get("type", "unknown")
            timestamp = datetime.fromtimestamp(msg.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
            
            if msg_type == "message":
                sender = msg.get("sender", "")[:16] + "..."
                recipient = msg.get("recipient", "")[:16] + "..."
                click.echo(f"  [{timestamp}] SENT: {sender} → {recipient}")
            elif msg_type == "received":
                sender = msg.get("sender", "")[:16] + "..."
                click.echo(f"  [{timestamp}] RECV: from {sender}")
            elif msg_type == "broadcast":
                click.echo(f"  [{timestamp}] BROADCAST")
        
        click.echo()
    else:
        click.echo("No message history.")


if __name__ == "__main__":
    cli()
