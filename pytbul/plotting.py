import seaborn
from matplotlib.figure import Figure


def tests_results_evolution(df, skill: str, display_tests: bool, display_quartiles: bool):
    fig = Figure(figsize=(10, 5), dpi=80)
    ax = fig.add_subplot(111)

    if skill is not None:
        adf = df.query('skill == "%s"' % skill)
    else:
        adf = df

    ndf = (
        adf[['date', 'weighted_result']]
            .dropna()
            .groupby(['date'])
            .describe()
            .unstack()
            .loc[:, ('weighted_result', ['mean', '25%', '50%', '75%'])]
            .T
            .reset_index(level=0, drop=True)
            .T
    )

    ax = ndf[['mean', '50%']].plot(style=['b--', 'g'], ax=ax)

    if display_quartiles:
        ax.fill_between(ndf.index, ndf['25%'], ndf['75%'], color='green', alpha='0.1')

    ax.xaxis.grid(False)
    ax.set_ylim(0, 20)
    ax.axhline(10, color='r', alpha=0.1)
    ax.set_ylabel('({})'.format(skill or 'toutes les compétences'))
    ax.xaxis.set_visible(False)

    if display_tests:
        for x in adf[['period', 'date']].groupby('period').min()['date']:
            ax.axvline(x, 0, 20, color='r', ls='dotted')

        for date, row in adf.groupby(['date']).agg({'code': 'first'}).iterrows():
            ax.axvline(date, -3, 20, color='b', alpha=0.1)
            ax.text(date, -0.2, row['code'], rotation=90, horizontalalignment='center', verticalalignment='top')

    return fig


def results_overview(df, normalized: bool, group_by: str, skill: str):
    fig = Figure(figsize=(10, 5), dpi=80)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.20)

    minx, maxx = (-2, 2) if normalized else (0, 20)

    ndf = df.sort_values(by='name').rename(columns={'weighted_result': 'bruts', 'normalized_result': 'normalisés'})

    if skill is not None:
        ndf = ndf.query('skill == "%s"' % skill)

    field = 'bruts' if not normalized else 'normalisés'

    ax = seaborn.boxplot(data=ndf, x=field, y=group_by, orient='h', ax=ax)
    ax.set_xlim(minx, maxx)
    ax.axvline((maxx - minx) / 2, color='r', ls='dotted')
    ax.set_title('Vue générale ({})'.format(field))

    return fig


def skills_distribution(df, by_number: bool):
    ndf = (df
           .drop_duplicates('code')
           .groupby(['period', 'skill'])[['weight']]
           .agg([sum, len])
           .sort_index()
           .unstack()
           )

    ndf.loc['total'] = ndf.sum()

    fig = Figure(figsize=(10, 5), dpi=80)
    ax = fig.add_subplot(111)

    if by_number:
        ndf['weight', 'len'].plot(kind='bar', title='En nombre', ax=ax)
        ax.set_title('Répartition des compétences (en nombre)')
    else:
        ndf['weight', 'sum'].plot(kind='bar', title='En poids', ax=ax)
        ax.set_title('Répartition des compétences (en poids)')

    return fig


def student_results(df, student: str, normalized: bool, regression: bool, display_tests: bool, skill: str):
    miny, maxy = (-2, 2) if normalized else (0, 20)
    field = 'bruts' if not normalized else 'normalisés'

    ndf = (
        df.assign(temps=(df['date'] - min(df['date'])).dt.days)
            .rename(columns={'weighted_result': 'bruts', 'normalized_result': 'normalisés'})
            .query('name == "%s"' % student)
    )

    if skill is not None:
        ndf = ndf.query('skill == "%s"' % skill)

    fig = Figure(figsize=(10, 5), dpi=80)
    ax = fig.add_subplot(111)

    ax.axhline((maxy - miny) / 2, color='r', alpha=0.2)
    ax.set_ylim(miny, maxy)

    if len(ndf) > 0:
        ndf.set_index('temps')[field].plot(ax=ax)
        if regression:
            seaborn.regplot('temps', field, data=ndf, color=seaborn.color_palette()[0], ax=ax, scatter=False,
                            line_kws={'linestyle': '--'})

    if display_tests:
        fig.subplots_adjust(bottom=0.20)

        for x in ndf[['period', 'temps']].groupby('period').min()['temps']:
            ax.axvline(x, miny, maxy, color='r', ls='dotted')

        for date, row in ndf.groupby(['temps']).agg({'code': 'first'}).iterrows():
            ax.axvline(date, miny - 3, maxy, color='b', alpha=0.1)
            ax.text(date, miny - (maxy - miny) / 100, row['code'], rotation=90, horizontalalignment='right',
                    verticalalignment='top')

    ax.set_title('{} ({})'.format(student, skill or 'toutes les compétences'))
    ax.set_ylabel(field)
    ax.hold(False)
    ax.xaxis.set_visible(False)

    return fig
