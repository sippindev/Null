# Null

Null is a modern desktop crypto wallet focused on clean design, local security, and practical privacy controls.

It is being built as a dark, polished wallet experience with support for multiple networks, local encrypted storage, optional proxy routing, and a simple user-first interface.

## Features

- Clean dark desktop wallet UI
- Local-only wallet data storage
- Encrypted sensitive data at rest
- Optional proxy support for network privacy
- Multi-network architecture
- Send, receive, and refresh wallet actions
- Privacy & Network settings tab
- Structured debug logging without exposing secrets
- Modern wallet-style interface inspired by premium desktop wallets

## Privacy

Null is designed to reduce unnecessary data exposure.

- Wallet data is stored locally on the device
- Sensitive information is encrypted
- No unnecessary analytics or tracking
- Optional proxy support can help hide the user's IP from RPC providers and blockchain services
- Logs should never expose private keys, seed phrases, passwords, or proxy credentials

Important: Most blockchains are public by design. Null can help protect network identity, but it does not hide transactions on public blockchains.

## Proxy Support

Null supports optional proxy routing for supported network requests.

Proxy format:

```text
hostname:port:username:password
