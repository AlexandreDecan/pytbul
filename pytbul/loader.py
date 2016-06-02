import pandas
import pyexcel_xls
import datetime

from itertools import takewhile


def load_from_xls(filepath, *,
                  names_sheet='Nom',
                  tests_sheets=['B1', 'B2', 'B3', 'B4'],
                  tests_dates=[(2015, 9), (2015, 11), (2016, 2), (2016, 4), (2016, 6)],
                  tests_stopwords=['', 'Total SSFL'],
                  name_pos=(3, 1),
                  test_pos=(0, 2),
                  max_decal=1,
                  comp_decal=2,
                  norm_weight=20):
    results = []

    data = pyexcel_xls.get_data(filepath)

    students = []
    for line in data[names_sheet][name_pos[0]:]:
        try:
            name = line[name_pos[1]]
            if name:
                students.append(name)
        except IndexError as e:
            pass

    for sheet in tests_sheets:
        _ = data[sheet][test_pos[0]][test_pos[1]:]
        tests = list(takewhile(lambda s: s not in tests_stopwords, _))
        maxs = data[sheet][test_pos[0] + max_decal][test_pos[1]:test_pos[1] + len(tests)]
        comps = data[sheet][test_pos[0] + comp_decal][test_pos[1]:test_pos[1] + len(tests)]
        for student_i, student in enumerate(students):
            if len(tests) == 0:
                continue

            year, month = tests_dates[tests_sheets.index(sheet)]
            tests_start = datetime.datetime(year=year, month=month, day=1)

            year, month = tests_dates[tests_sheets.index(sheet) + 1]
            tests_end = datetime.datetime(year=year, month=month, day=1)

            tests_interval = (tests_end - tests_start).days // len(tests)

            for test_i, test in enumerate(tests):
                row = name_pos[0] + student_i
                column = test_pos[1] + test_i
                value = data[sheet][row][column]

                if value != 0 and not value:
                    value = pandas.np.nan

                test_date = tests_start + datetime.timedelta(days=test_i * tests_interval)

                result = {
                    'name': student,
                    'period': sheet,
                    'date': test_date,
                    'code': '%s/%02d/%s' % (sheet, test_i + 1, comps[test_i]),
                    'test': '%s' % test,
                    'weight': maxs[test_i],
                    'skill': comps[test_i],
                    'result': value
                }

                results.append(result)

    df = pandas.DataFrame.from_dict(results)
    df['weighted_result'] = df['result'] / df['weight'] * norm_weight

    tests = df.dropna().groupby('date')['result'].describe().unstack()[['mean', '25%', '50%', '75%']]
    ndf = df.merge(tests, how='outer', left_on=['date'], right_index=True)
    ndf['range'] = (ndf['75%'] - ndf['25%'])
    ndf['normalized_result'] = (ndf['result'] - ndf['50%']) / ndf['range']

    ndf['normalized_result'] = ndf['normalized_result'].where(ndf['range'] > 0, 0)
    ndf['normalized_result'] = ndf['normalized_result'].where(ndf['result'].notnull(), pandas.np.nan)
    ndf = ndf.drop('range', axis=1)

    return ndf
