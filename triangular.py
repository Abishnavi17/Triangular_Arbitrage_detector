import math
import time
from typing import Dict, List, Tuple, Optional

class TriangularArbitrageDetector:
    def __init__(self, assets: List[str], transaction_fee: float = 0.001):
        """
        Initializes the detector with a clean asset matrix setup.
        :param assets: List of ticker strings e.g., ['USD', 'EUR', 'GBP', 'BTC']
        :param transaction_fee: Flat trading fee rate per transaction (0.001 = 0.1%)
        """
        self.assets = assets
        # Fast index mapping to avoid heavy string lookups during loops
        self.asset_to_idx = {asset: i for i, asset in enumerate(assets)}
        self.idx_to_asset = {i: asset for i, asset in enumerate(assets)}
        self.num_assets = len(assets)
        self.fee = transaction_fee
        
        # Graph stores the mathematically transformed weights (-ln(rate))
        self.graph = [[float('inf')] * self.num_assets for _ in range(self.num_assets)]
        # Stores the raw, untouched rates used later for absolute profit validation
        self.real_rates = [[0.0] * self.num_assets for _ in range(self.num_assets)]

    def add_rate(self, source_asset: str, target_asset: str, rate: float):
        """
        Populates exchange rates between assets and transforms them using negative logs.
        """
        if source_asset not in self.asset_to_idx or target_asset not in self.asset_to_idx:
            return
            
        u = self.asset_to_idx[source_asset]
        v = self.asset_to_idx[target_asset]
        
        # Save the raw rate for real-world simulation checks
        self.real_rates[u][v] = rate
        
        # Apply the negative log transform factoring in the exchange fee
        # Mathematical Trick: Multiplication becomes addition via logs
        effective_rate = rate * (1.0 - self.fee)
        if effective_rate > 0:
            self.graph[u][v] = -math.log(effective_rate)

    def find_arbitrage_loops(self) -> Optional[List[Tuple[str, float]]]:
        """
        Executes the Bellman-Ford algorithm to identify negative weight cycles.
        """
        n = self.num_assets
        dist = [float('inf')] * n
        predecessor = [-1] * n
        
        # Anchor the algorithm starting point at the first asset index
        dist[0] = 0 
        
        # Phase 1: Relax all edges across the network (|V| - 1) times
        for _ in range(n - 1):
            for u in range(n):
                for v in range(n):
                    if self.graph[u][v] != float('inf'):
                        if dist[u] + self.graph[u][v] < dist[v]:
                            dist[v] = dist[u] + self.graph[u][v]
                            predecessor[v] = u

        # Phase 2: Run a final iteration to detect negative cycles
        for u in range(n):
            for v in range(n):
                if self.graph[u][v] != float('inf'):
                    # If a path distance can STILL be optimized, a negative loop exists
                    if dist[u] + self.graph[u][v] < dist[v]:
                        return self._reconstruct_cycle(v, predecessor)
        return None

    def _reconstruct_cycle(self, start_node: int, predecessor: List[int]) -> List[Tuple[str, float]]:
        """
        Traces backward through the breadcrumb trail to capture the asset loop sequence.
        """
        visited = set()
        curr = start_node
        
        # Walk deep into the predecessor map to guarantee we are inside the cyclic loop
        while curr not in visited:
            visited.add(curr)
            curr = predecessor[curr]
            if curr == -1:
                return []
                
        cycle_start = curr
        cycle_path = [cycle_start]
        
        # Trace the loop nodes step by step until we come back to where we started
        next_node = predecessor[cycle_start]
        while next_node != cycle_start:
            cycle_path.append(next_node)
            next_node = predecessor[next_node]
        cycle_path.append(cycle_start)
        
        # Reverse the trace so the execution path reads forward in time
        cycle_path.reverse()
        
        # Structure the final path into pairs with their corresponding rates
        readable_path = []
        for i in range(len(cycle_path) - 1):
            u = cycle_path[i]
            v = cycle_path[i+1]
            readable_path.append((self.idx_to_asset[u], self.real_rates[u][v]))
            
        # Add the final asset closing token anchor
        readable_path.append((self.idx_to_asset[cycle_path[-1]], 1.0))
        return readable_path

    def calculate_expected_roi(self, path: List[Tuple[str, float]]) -> float:
        """
        Simulates the entire loop with $1.00 of starting capital to verify real cash ROI.
        """
        if not path or len(path) < 3:
            return 0.0
            
        capital = 1.0  # Start with 1 base unit of currency
        
        # Run through the trade path sequentially, stripping trading fees at every point
        for i in range(len(path) - 1):
            source = path[i][0]
            target = path[i+1][0]
            u = self.asset_to_idx[source]
            v = self.asset_to_idx[target]
            
            raw_rate = self.real_rates[u][v]
            capital = (capital * raw_rate) * (1.0 - self.fee)
            
        return (capital - 1.0) * 100  # Formatted as a readable net profit percentage

# =====================================================================
# Main Simulation Launchpad
# =====================================================================
if __name__ == "__main__":
    # 1. Define our assets
    market_assets = ['USD', 'EUR', 'GBP', 'BTC']
    
    # 2. Setup detector with a standard 0.1% exchange trade fee
    detector = TriangularArbitrageDetector(assets=market_assets, transaction_fee=0.001)
    
    print("[*] Instantiating asset market matrix and populating live pairs...")
    
    # Standard, balanced market rates (No arbitrage here)
    detector.add_rate('USD', 'EUR', 0.92)   # $1 USD = 0.92 EUR
    detector.add_rate('EUR', 'GBP', 0.86)   # 1 EUR = 0.86 GBP
    detector.add_rate('GBP', 'USD', 1.26)   # 1 GBP = 1.26 USD
    
    # Let's artificially inject an active pricing anomaly across BTC routes
    # Normal: USD -> BTC -> EUR -> USD
    detector.add_rate('USD', 'BTC', 0.000015)  # Buying Bitcoin at ~$66,666/BTC
    detector.add_rate('BTC', 'EUR', 64500.0)   # Selling Bitcoin at an overvalued EUR rate 
    detector.add_rate('EUR', 'USD', 1.09)      # Converting back to USD at a high rate
    
    # 3. Trigger the Core Optimization Search Engine
    start_time = time.perf_counter()
    arbitrage_loop = detector.find_arbitrage_loops()
    execution_latency = (time.perf_counter() - start_time) * 1000 # in milliseconds
    
    print(f"[*] Engine successfully completed execution scan in {execution_latency:.4f} ms.")
    
    # 4. Output the results
    if arbitrage_loop:
        print("\n[!] SUCCESS: PROFITABLE ARBITRAGE PATH IDENTIFIED!")
        path_string = " -> ".join([asset for asset, _ in arbitrage_loop])
        print(f"    Execution Path: {path_string}")
        
        # Final Verification Check
        net_roi = detector.calculate_expected_roi(arbitrage_loop)
        print(f"\n[*] Net Expected Return (With Fees Deducted): {net_roi:.4f}%")
        
        if net_roi > 0:
            print(">>> CRITICAL ACTION STATUS: TRADE SIGNAL IS VIABLE FOR PRODUCTION EXECUTION.")
        else:
            print(">>> CRITICAL ACTION STATUS: ABORT. Profits are completely eaten by transaction fees.")
    else:
        print("\n[-] SCAN COMPLETE: Markets stable. No profitable mispricings found.")