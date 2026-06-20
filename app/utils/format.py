from datetime import datetime
import locale

DAYS_FR = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}

MONTHS_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

def formater_date_heure_en_francais(dt: datetime) -> str:
    """
    Formate un datetime en 'Lundi 22 Février 2025 à 14h30'.
    """
    day_name = DAYS_FR[dt.weekday()]
    month_name = MONTHS_FR[dt.month]

    return (
        f"{day_name} "
        f"{dt.day:02d} "
        f"{month_name} "
        f"{dt.year} "
        f"à {dt.hour:02d}h{dt.minute:02d}"
    )
