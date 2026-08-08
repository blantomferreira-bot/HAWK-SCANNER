"""Audited, mandatory consultations for every configured market and on-chain source."""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from hawk_worker.config import ScannerSettings


@dataclass(frozen=True)
class SourceConsultation:
    source: str
    status: str
    detail: str | None = None


class MandatorySourceRegistry:
    required_sources = (
        "coingecko", "coinglass", "defillama", "binance", "coinbase", "hyperliquid", "bitquery", "covalent",
        "alchemy", "moralis", "etherscan", "bscscan", "arbiscan", "basescan", "solscan",
    )

    def __init__(self, settings: ScannerSettings) -> None:
        self.settings = settings

    async def consult_all(self) -> list[SourceConsultation]:
        async with httpx.AsyncClient(timeout=30) as client:
            return await asyncio.gather(*(self._consult(client, source) for source in self.required_sources))

    async def _consult(self, client: httpx.AsyncClient, source: str) -> SourceConsultation:
        key = self.settings.source_api_keys.get(source, "")
        try:
            method, url, kwargs = self._request(source, key)
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return SourceConsultation(source, "AVAILABLE")
        except ValueError as error:
            return SourceConsultation(source, "NOT_CONFIGURED", str(error))
        except Exception as error:
            return SourceConsultation(source, "FAILED", str(error))

    @staticmethod
    def _request(source: str, key: str) -> tuple[str, str, dict[str, Any]]:
        if source == "coingecko":
            return "GET", "https://api.coingecko.com/api/v3/ping", {"headers": {"x-cg-pro-api-key": key} if key else {}}
        if source == "coinglass":
            if not key: raise ValueError("COINGLASS_API_KEY is required")
            return "GET", "https://open-api-v4.coinglass.com/api/futures/supported-coins", {"headers": {"CG-API-KEY": key}}
        if source == "defillama":
            if not key: raise ValueError("DEFILLAMA_API_KEY is required")
            return "GET", "https://pro-api.llama.fi/protocols", {"headers": {"Authorization": f"Bearer {key}"}}
        if source == "binance":
            return "GET", "https://data-api.binance.vision/api/v3/ping", {}
        if source == "coinbase":
            return "GET", "https://api.coinbase.com/api/v3/brokerage/market/products", {}
        if source == "hyperliquid":
            return "POST", "https://api.hyperliquid.xyz/info", {"json": {"type": "metaAndAssetCtxs"}}
        if source == "bitquery":
            if not key: raise ValueError("BITQUERY_API_KEY is required")
            return "POST", "https://streaming.bitquery.io/graphql", {"headers": {"Authorization": f"Bearer {key}"}, "json": {"query": "query { EVM(network: eth) { Blocks(limit: {count: 1}) { count } } }"}}
        if source == "covalent":
            if not key: raise ValueError("COVALENT_API_KEY is required")
            return "GET", "https://api.covalenthq.com/v1/eth-mainnet/block_v2/latest/", {"params": {"key": key}}
        if source == "alchemy":
            if not key: raise ValueError("ALCHEMY_API_KEY is required")
            return "POST", f"https://eth-mainnet.g.alchemy.com/v2/{key}", {"json": {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}}
        if source == "moralis":
            if not key: raise ValueError("MORALIS_API_KEY is required")
            return "GET", "https://deep-index.moralis.io/api/v2.2/block/latest", {"headers": {"X-API-Key": key}}
        if source in {"etherscan", "bscscan", "arbiscan", "basescan"}:
            if not key: raise ValueError(f"{source.upper()}_API_KEY is required")
            chain_ids = {"etherscan": "1", "bscscan": "56", "arbiscan": "42161", "basescan": "8453"}
            return "GET", "https://api.etherscan.io/v2/api", {"params": {"chainid": chain_ids[source], "module": "proxy", "action": "eth_blockNumber", "apikey": key}}
        if source == "solscan":
            if not key: raise ValueError("SOLSCAN_API_KEY is required")
            return "GET", "https://pro-api.solscan.io/v2.0/chain/info", {"headers": {"token": key}}
        raise ValueError(f"Unknown source: {source}")
