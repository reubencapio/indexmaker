#!/usr/bin/env python3
"""
AI-Powered Index Creation Example

This example demonstrates how to use the IndexAI class to create
financial indices from natural language descriptions.

Requirements:
    pip install indexmaker[ai]
    export OPENAI_API_KEY="your-api-key"

Usage:
    python ai_index_creation.py "Your index description"
    python ai_index_creation.py --interactive
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Create financial indices from natural language descriptions"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Natural language description of the index to create",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode - enter descriptions interactively",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for the index configuration (JSON)",
    )
    parser.add_argument(
        "--save-index",
        "-s",
        help="Save the created index to a JSON file",
    )

    args = parser.parse_args()

    # Check for API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key required.")
        print("Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)

    try:
        from indexmaker.ai import IndexAI, IndexAIConfig
    except ImportError:
        print("Error: AI features require the openai package.")
        print("Install with: pip install indexmaker[ai]")
        sys.exit(1)

    # Create the AI instance
    config = IndexAIConfig(api_key=api_key, model=args.model)
    ai = IndexAI(config=config)

    if args.interactive:
        interactive_mode(ai, args)
    elif args.description:
        create_index(ai, args.description, args)
    else:
        # Show some example prompts
        print("=" * 60)
        print("IndexMaker AI - Create indices from natural language")
        print("=" * 60)
        print()
        print("Example prompts:")
        print()
        print('  "Create an equal-weight index of the FAANG stocks"')
        print()
        print('  "Create a US large-cap technology index with the top 20 tech')
        print('   companies by market cap, with a 10% single stock cap"')
        print()
        print('  "Create a global dividend index with stocks yielding over 4%,')
        print('   weighted by dividend yield, rebalancing semi-annually"')
        print()
        print('  "Create an ESG-screened index of European banks, excluding')
        print('   any involved in controversial weapons or thermal coal"')
        print()
        print("Usage:")
        print('  python ai_index_creation.py "Your description here"')
        print("  python ai_index_creation.py --interactive")
        print()


def create_index(ai, description: str, args):
    """Create an index from a description."""
    print()
    print("Creating index...")
    print("-" * 40)

    try:
        result = ai.create_index(description)

        print()
        print(f"✅ Created: {result.index.name}")
        print(f"   Identifier: {result.index.identifier}")
        print(f"   Currency: {result.index.currency}")
        print(f"   Base Value: {result.index.base_value}")
        print()
        print("Explanation:")
        print("-" * 40)
        print(result.explanation)
        print()

        # Show configuration
        print("Configuration:")
        print("-" * 40)
        config_json = json.dumps(result.config, indent=2, default=str)
        print(config_json)
        print()

        # Save if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result.config, f, indent=2, default=str)
            print(f"Configuration saved to: {args.output}")

        if args.save_index:
            result.index.save(args.save_index)
            print(f"Index saved to: {args.save_index}")

        return result.index

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def interactive_mode(ai, args):
    """Interactive mode for creating indices."""
    print()
    print("=" * 60)
    print("IndexMaker AI - Interactive Mode")
    print("=" * 60)
    print()
    print("Describe the index you want to create, or type 'quit' to exit.")
    print("Type 'examples' to see example prompts.")
    print()

    while True:
        try:
            description = input("\n📊 Describe your index: ").strip()

            if not description:
                continue

            if description.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if description.lower() == "examples":
                show_examples()
                continue

            if description.lower() == "help":
                show_help()
                continue

            create_index(ai, description, args)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            break


def show_examples():
    """Show example prompts."""
    print()
    print("Example prompts:")
    print("-" * 40)
    examples = [
        "Create an equal-weight index of the FAANG stocks",
        "Top 50 US technology companies by market cap",
        "European dividend aristocrats, weighted by yield",
        "Global clean energy index with 30 constituents",
        "US small-cap value stocks, quarterly rebalanced",
        "Emerging markets banks index, capped at 10% per stock",
        "AI and robotics thematic index",
        "ESG-screened S&P 500 alternative",
    ]
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. {ex}")
    print()


def show_help():
    """Show help information."""
    print()
    print("Available commands:")
    print("-" * 40)
    print("  examples  - Show example index descriptions")
    print("  help      - Show this help message")
    print("  quit      - Exit interactive mode")
    print()
    print("Tips for good descriptions:")
    print("-" * 40)
    print("  - Specify the region (US, Europe, Global, etc.)")
    print("  - Mention the number of constituents if important")
    print("  - Specify weighting method (equal, market cap, etc.)")
    print("  - Include any caps or constraints")
    print("  - Mention rebalancing frequency if not quarterly")
    print()


if __name__ == "__main__":
    main()


