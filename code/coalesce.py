import re
from pathlib import Path

import pandas as pd

# 1. Load each month for each forecast element
# 2. For each month:
#   1. Remove missing values, i.e. 9999 (is this the same missing value for all datasets?)
#   2. Take last forecast time for each valid_time within each x/y box
#       a = sdf.sort_values(['x', 'y', 'valid_time', 'fcst_time'])
#       result = a.drop_duplicates(['x', 'y', 'valid_time'], keep='last')
#   3. Save to new dataset?
# 3. Load all days
#   - Take last forecast time for each valid_time within each x/y box

data_dir = Path('../data/ygu/')


def main(data_dir):
    files = data_dir.iterdir()
    names = create_file_names_df(files)

    # Find unique month periods for all files
    months = names['date'].dt.to_period('M').unique()
    # Find unique forecast types for all files
    fcst_types = names['prefix'].unique()

    # Create generator to loop over product of months and fcst_types
    gen = ((month, fcst_type) for month in months for fcst_type in fcst_types)
    for month, fcst_type in gen:
        matching = names[(month.start_time <= names['date'])
                         & (names['date'] <= month.end_time)]
        matching = matching[matching['prefix'] == fcst_type]

        if len(matching) > 0:
            data = load_files(matching['path'])


def load_files(paths):
    """Load data from paths and keep most recent forecast for each valid_time

    Args:
        - paths: file paths to data files

    Returns:
        DataFrame: single DF with one row per x-y-valid_time combo. Same columns
        as original files.
    """
    dfs = [pd.read_parquet(f) for f in paths]
    df = pd.concat(dfs, sort=False)

    # Remove missing values. It's 9999 in the max temp/YGU dataset, but not sure
    # if it's that in all forecast elements
    MISSING = 9999
    df = df[df['vals'] != MISSING]

    # Sort by 'x', 'y', 'valid_time', and then 'fcst_time'
    df = df.sort_values(['x', 'y', 'valid_time', 'fcst_time'])
    # Now within 'x', 'y', 'valid_time', take the last row. This should be the
    # last fcst_time for each valid_time and x/y cell
    df = df.drop_duplicates(['x', 'y', 'valid_time'], keep='last')

    return df


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

