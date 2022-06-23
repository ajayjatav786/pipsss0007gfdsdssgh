"""FolderParser: a parser of information from folders with Airflow modules."""


from glob import glob
import os
import pathlib

# 'log', 'secrets',
_TARGETS = ["operators", "sensors", "hooks", "transfers"]
_INVALID_FILES = ["__init__.py"]


class FolderParser:
    """Implements the main functionallity of the FolderParser module"""

    def __init__(self, location):
        self.location = location
        self.files = []

    def collect(self, filter_by_targets: bool = False):
        """Collects interesting files from the specified folder"""
        # pylint: disable=unused-variable
        self.files = [
            f.path
            for f in os.scandir(self.location)
            if f.is_file() and f.name not in _INVALID_FILES and pathlib.Path(f.name).suffix == ".py"
        ]
        for root, dirs, files in os.walk(self.location):
            for dirname in dirs:
                if not filter_by_targets or dirname in _TARGETS:
                    filenames = glob(os.path.join(root, dirname) + "/*.py")
                    self.files.extend([f for f in filenames if os.path.basename(f) not in _INVALID_FILES])

    def filter(self):
        """Filters deprecated files."""
        # pylint: disable=no-self-use
        # TODO
        # * What about ../airflow/airflow/utils/log ? (not in Astronomer)
        # * What about ../airflow/airflow/contrib/* ? (deprecated?)
        yield

    def parse(self):
        """Parses interesting info from files."""
        # pylint: disable=no-self-use
        yield

    def dump(self):
        """Dumps the internal list of collected files."""
        print("\n".join(self.files))

    def stats(self):
        """Prints some stats."""
        stats = {}
        for target in _TARGETS:
            stats[target] = 0
        for filename in self.files:
            for target in _TARGETS:
                if filename.find("/" + target + "/") > 0:
                    stats[target] += 1
        for key, value in stats.items():
            print("* {}: {}".format(key, value))
        print("Total: {}".format(len(self.files)))

    def get_files(self):
        """Dumps the internal list of collected files."""
        return self.files


if __name__ == "__main__":
    obj = FolderParser("airflow/airflow")
    obj.collect()
    obj.dump()
    obj.stats()
    listing = obj.get_files()
    print(f"{len(listing)} files found")
