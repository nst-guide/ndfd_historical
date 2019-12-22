import re
import pandas as pd
from pathlib import Path


def main(data_dir):
    files = data_dir.iterdir()
    names = create_file_names_df(files)


def create_file_names_df(files):
    """Create DataFrame with file metadata

    Given a list of files, create a DataFrame with columns:
    - prefix: forecast code, e.g. YEU
    - year
    - month
    - day
    - hour
    - minute
    - path

    Note that these dates come from the filename, so they should not be
    considered exact.
    """
    regex = r'^([A-Z]{3})Z98_[A-Z]{4}_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})'
    # groups: prefix, year, month, day, hour, minute
    all_rows = []
    for file in files:
        row = list(re.match(regex, file.name).groups())
        row.append(str(file))
        all_rows.append(row)

    # Create dataframe
    cols = ['prefix', 'year', 'month', 'day', 'hour', 'minute', 'path']
    names = pd.DataFrame(all_rows, columns=cols)

    # Coerce numeric columns to numeric dtype
    date_cols = ['year', 'month', 'day', 'hour', 'minute']
    for col in date_cols:
        names[col] = pd.to_numeric(names[col])

    # Create timestamp column
    names['date'] = pd.to_datetime(names[date_cols])

    # Drop date components
    names = names.drop(date_cols, axis=1)

    return names


if __name__ == '__main__':
    main()

