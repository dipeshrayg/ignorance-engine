"""Runs the two remaining OpenAlex-dependent jobs back to back. Safe to fire
and forget -- data/openalex_client.py self-paces and, if the quota is still
exhausted when this starts, the client's own 429 retry path sleeps out the
reset automatically before the first real request goes through.
"""
from data import subfield_explore, time_machine_benchmark

if __name__ == "__main__":
    print("=== Time-Machine Benchmark ===")
    if time_machine_benchmark.verify_syntax():
        time_machine_benchmark.run_benchmark()

    print("\n=== Subfield-level cross-domain exploration ===")
    subfield_explore.run()

    print("\n=== done ===")
