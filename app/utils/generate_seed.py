import json
from typing import Any

from app.utils.generators import (
    generate_change_events,
    generate_institutions,
    generate_persons,
    generate_read_events,
)


def calculate_code_distribution(changes: list[dict[str, Any]]) -> dict[str, int]:
    """
    Calculate the distribution of change codes in the provided list of changes.

    This function processes a list of dictionaries, where each dictionary represents a change
    record. Each record contains a "change_code" key. The function calculates the frequency
    of each unique "change_code" across all the changes and returns the result as a dictionary.

    :param changes: A list of dictionaries, where each dictionary must include a "change_code"
        key that represents a specific type of change.
    :type changes: list[dict[str, Any]]

    :return: A dictionary where the keys are unique change codes and the values are their
        respective counts in the provided list of changes.
    :rtype: dict[str, int]
    """
    code_counts = {}
    for change in changes:
        code = change["change_code"]
        code_counts[code] = code_counts.get(code, 0) + 1
    return code_counts


def print_statistics(
        num_institutions: int,
        num_persons: int,
        num_changes: int,
        num_reads: int,
        changes: list[dict[str, Any]]
) -> None:
    """
    Prints detailed statistics of generated seed data, including counts of institutions,
    persons, change events, read events, and distribution of change event codes.

    :param num_institutions: The total number of institutions in the seed data.
    :type num_institutions: int
    :param num_persons: The total number of persons in the seed data.
    :type num_persons: int
    :param num_changes: The total number of change events in the seed data.
    :type num_changes: int
    :param num_reads: The total number of read events in the seed data.
    :type num_reads: int
    :param changes: A list of dictionaries, where each dictionary represents a change
        event containing relevant fields and data.
    :type changes: list[dict[str, Any]]
    :return: None
    """
    print(f"Generating seed data:")
    print(f"  - Institutions: {num_institutions}")
    print(f"  - Persons: {num_persons}")
    print(f"  - Change events: {num_changes}")
    print(f"  - Read events: {num_reads}")

    print(f"\nGenerated seed_data.json:")
    print(f"   Total change events: {len(changes)}")
    print(f"   Total read events: {num_reads}")
    print(f"   Change code distribution:")

    code_counts = calculate_code_distribution(changes)
    for code, count in sorted(code_counts.items()):
        print(f"     - {code}: {count}")


def generate(
        num_institutions: int = 10,
        num_persons: int = 50,
        num_changes: int = 200,
        num_reads: int = 30
) -> None:
    """
    Generates and writes seed data to a JSON file, simulating institutions, persons, and event
    activities (changes and reads). Prints a summary of the generated data to the console.

    :param num_institutions: Number of institutions to generate.
    :type num_institutions: int
    :param num_persons: Number of persons to generate.
    :type num_persons: int
    :param num_changes: Number of change events to generate.
    :type num_changes: int
    :param num_reads: Number of read events to generate.
    :type num_reads: int
    :return: None
    """
    institutions = generate_institutions(num_institutions)
    persons = generate_persons(num_persons)
    changes = generate_change_events(num_changes, persons, institutions)
    reads = generate_read_events(num_reads, persons, institutions)

    data = {
        "institutions": institutions,
        "persons": persons,
        "events": {
            "reads": reads,
            "changes": changes
        }
    }

    with open("seed_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print_statistics(num_institutions, num_persons, num_changes, num_reads, changes)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate seed data for audit service with institutions, persons, and events.'
    )
    parser.add_argument(
        '--institutions',
        type=int,
        default=20,
        help='Number of institutions to generate (default: 20)'
    )
    parser.add_argument(
        '--persons',
        type=int,
        default=100,
        help='Number of persons to generate (default: 100)'
    )
    parser.add_argument(
        '--changes',
        type=int,
        default=500,
        help='Number of change events to generate (default: 500)'
    )
    parser.add_argument(
        '--reads',
        type=int,
        default=50,
        help='Number of read events to generate (default: 50)'
    )

    args = parser.parse_args()

    generate(
        num_institutions=args.institutions,
        num_persons=args.persons,
        num_changes=args.changes,
        num_reads=args.reads
    )
