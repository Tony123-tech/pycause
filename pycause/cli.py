import argparse
import os
import runpy
import sys
import traceback


class PyCauseCLIError(Exception):
    def __init__(self, message: str, original_exc: BaseException):
        super().__init__(message)
        self.original_exc = original_exc
        self.tb_str = "".join(
            traceback.format_exception(
                type(original_exc), original_exc, original_exc.__traceback__
            )
        )


def main():
    parser = argparse.ArgumentParser(
        description="PyCause: Run Python scripts with Natural Language Provenance."
    )
    parser.add_argument("script", help="Path to the Python script you want to execute.")
    parser.add_argument(
        "--lang",
        "-l",
        choices=["zh", "en"],
        help="Language for explanations (zh or en). If omitted, you will be prompted.",
    )

    args = parser.parse_args()
    script_path = args.script

    lang = args.lang
    if not lang:
        print("🌐 Please select a language for explanations:")
        print("  [1] Traditional Chinese (zh)")
        print("  [2] English (en)")
        choice = input("Enter choice (default 1): ").strip()
        lang = "en" if choice == "2" else "zh"
        print()

    os.environ["PYCAUSE_LANG"] = lang

    try:
        print(f"🐍 Running PyCause on {script_path} (lang={lang})...")
        print("-" * 40)
        runpy.run_path(script_path, run_name="__main__")
        print("-" * 40)
        print("✅ Execution finished.")

    except FileNotFoundError:
        print(f"❌ Error: File '{script_path}' not found.")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n🛑 Execution interrupted by user.")
        sys.exit(130)

    except SystemExit:
        raise

    except Exception as e:
        cli_error = PyCauseCLIError(f"Runtime Error in {script_path}", e)

        print("-" * 40)
        print(f"💥 {cli_error}")
        print("\n🔍 Traceback:")
        print(cli_error.tb_str)
        print("💡 Tip: Check your script for undefined variables or math errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
