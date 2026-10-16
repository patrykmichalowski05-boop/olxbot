from pathlib import Path


def database_file(
    folder,
    name='observations.sqlite'
):
    if name != 'observations.sqlite':
        raise ValueError(
            'Nieznana nazwa bazy'
        )

    base = Path(folder)

    if (
        base.is_symlink()
        or not base.is_dir()
    ):
        raise ValueError(
            'Brak bezpiecznego sandbox'
        )

    base = base.resolve(strict=True)
    prod = Path('/opt/olx-bot')

    if (
        base == prod
        or prod in base.parents
    ):
        raise ValueError(
            'Katalog produkcyjny zabroniony'
        )

    db = base / name

    if (
        db.is_symlink()
        or not db.is_file()
    ):
        raise ValueError(
            'Brak bazy testowej lub symlink'
        )

    if db.resolve(strict=True).parent != base:
        raise ValueError(
            'Sciezka poza sandbox'
        )

    return db
