from datetime import datetime
import locale
def formater_date_heure_en_francais(date_obj: datetime) -> str:

    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "fr_FR")
        except locale.Error:
            pass

    # %H = Heure (00-23), %M = Minute (00-59)
    date_str = date_obj.strftime("%A %d %B %Y à %Hh%M")

    return date_str.capitalize()
