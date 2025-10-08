import _core.extension as extension 
import concurrent.futures
import process.ci_suggester.etl as ci_suggester_etl

class Process:
    def __init__(self):
        pass

    def run(self):
        # List to track success or failure of each export iteration
        process_success = []

        process_success.append(ci_suggester_etl.Process().run())

        return extension.Common.check_for_success(process_success)