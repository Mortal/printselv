import argparse
import datetime
import os
import re
import subprocess
import traceback
from typing import NamedTuple, Optional


parser = argparse.ArgumentParser()
parser.add_argument("filename", nargs="+")


class PrintSelvBillet(NamedTuple):
    year: int
    month: int
    day: int
    from_h: int
    from_m: int
    to_h: int
    to_m: int
    fra: str
    til: str
    kontrol: str
    billettype: str
    tognr: str
    vogn: str
    plads: str
    antal: str
    pladstype: str


def parse_text(
    t_bytes: bytes, date_hint: Optional[datetime.date] = None
) -> PrintSelvBillet:
    t = t_bytes.decode("utf-8").replace(chr(65533), " ")
    lines = (line for line in t.splitlines() if line.strip())
    line = next(lines)
    assert "Print Selv-billet" in line, line
    line = next(lines)
    SECTIONS = ("Billetoplysninger", "Pladsreservation", "VIGTIGT")
    billet_parts = []
    plads_parts = []
    TICKET_KINDS = (
        "Voksne",
        "Ledsagende børn",
        "Betalende børn",
        "65-Billetter",
        "Ung",
        "Ung (DSB WildCard)",
        "Ung (DSB Ung Kort)",
    )
    S_BASE = (
        "Afgang fra",
        "Ankomst til",
        "Pris i alt",
    )
    while not line.startswith("VIGTIGT"):
        kind = line
        if kind == "Billetoplysninger":
            S = S_BASE + ("Kontrolnummer", "Billettype")
            assert not billet_parts
            part = []
            billet_parts.append(part)
        elif kind == "Pladsreservation":
            S = S_BASE + ("Tognr", "Vognnr.", "Pladsnr.", "Antal", "Pladstype")
            assert not plads_parts
            part = []
            plads_parts.append(part)

        line = next(lines)
        dates = []
        times = []
        ticket_kinds = []
        ticket_counts = []
        preis = -1

        while not line.startswith(SECTIONS):
            if mo := re.match(r"^([0-9]+)\.([a-z]{3,4})\.?$", line):
                dates.append((int(mo.group(1)), mo.group(2)))
                assert 2 >= len(dates) == len(times) + 1, (dates, times)
            elif mo := re.match(r"^([0-9]{1,2}):([0-9]{1,2})$", line):
                times.append((int(mo.group(1)), int(mo.group(2))))
                assert 2 >= len(dates) == len(times), (dates, times)
            elif kind == "Billetoplysninger" and line in TICKET_KINDS:
                ticket_kinds.append(line)
            elif kind == "Billetoplysninger" and line == "-":
                ticket_counts.append(0)
            elif kind == "Billetoplysninger" and re.match(r"^[0-9]+$", line):
                ticket_counts.append(int(line))
            elif line.startswith("Via:"):
                pass
                # if line != "Via:" and line != "Via: se rejseplanen":
                #     print(line)
            elif line == "Københavns":
                line = "%s %s" % (line, next(lines))
                part.append(line)
            elif line.endswith("kr."):
                preis = int(line.rpartition("kr.")[0])
                assert preis >= 0
            elif line not in S:
                part.append(line)
            line = next(lines)
        if kind == "Billetoplysninger":
            assert len(part) == 4, (kind, part)
        elif kind == "Pladsreservation":
            if "InterCityLyn" in part:
                i = part.index("InterCityLyn")
                part[i] += " %s" % part.pop()
            assert len(part) == 7, (kind, part)

    assert line is not None
    assert "VIGTIGT" in line, line

    assert len(dates) == len(times) == 2
    from_day, from_month_str = dates[0]
    from_month = (
        "jan feb mar apr maj jun jul aug sep okt nov dec".split().index(from_month_str)
        + 1
    )
    (from_h, from_m), (to_h, to_m) = times

    rest = "\n".join(lines)
    fulldates_in_rest = list(
        re.finditer(r"\b([0-9]{1,2})\. ([a-z]{3,10}) (20[0-9]{2})\b", rest)
    )
    shortdates_in_rest = list(
        re.finditer(
            r"\b([0-9]{2})\.([0-9]{2})\.([0-9]{2}) ([0-9]{1,2}):([0-9]{2})\b", rest
        )
    )
    if shortdates_in_rest:
        mo = shortdates_in_rest[0]
        hint_day, hint_month, hint_shortyear, hint_hour, hint_minute = map(
            int, mo.groups()
        )
        hint_year = 2000 + hint_shortyear
        if date_hint is None:
            date_hint = datetime.date(hint_year, hint_month, hint_day)
    if fulldates_in_rest:
        mo = fulldates_in_rest[0]
        hint_day = int(mo.group(1))
        hint_month = 1 + "januar februar marts april maj juni juli august september oktober november december".split().index(
            mo.group(2)
        )
        hint_year = int(mo.group(3))
        if date_hint is None:
            date_hint = datetime.date(hint_year, hint_month, hint_day)
    year: Optional[int] = None
    if date_hint is not None:
        year = min(
            [date_hint.year, date_hint.year + 1],
            key=lambda y: abs(
                (date_hint - datetime.date(y, from_month, from_day)).days
            ),
        )
    assert year is not None
    fra = til = ""
    kontrol: Optional[str] = None
    billettype: Optional[str] = None
    tognr: Optional[str] = None
    vogn: Optional[str] = None
    plads: Optional[str] = None
    antal: Optional[str] = None
    pladstype: Optional[str] = None
    if billet_parts:
        kontrol, fra, til, billettype = billet_parts[0]
    if plads_parts:
        fra, til, tognr, vogn, plads, antal, pladstype = plads_parts[0]
    assert fra
    assert til
    return PrintSelvBillet(
        year,
        from_month,
        from_day,
        from_h,
        from_m,
        to_h,
        to_m,
        fra,
        til,
        kontrol,
        billettype,
        tognr,
        vogn,
        plads,
        antal,
        pladstype,
    )


def _fmt(b: PrintSelvBillet) -> str:
    billet_str = ""
    plads_str = ""
    fra = ""
    til = ""
    if typ := b.billettype:
        if "Standard" in typ:
            typ = "Standard"
        billet_str = typ.replace(" ", "").replace("'", "").replace("billet", "")
    if (
        (typ := b.pladstype)
        and (tognr := b.tognr)
        and (vogn := b.vogn)
        and (plads := b.plads)
    ):
        typ = typ.replace("'", "").replace("Standard", "").replace("zone", "").strip()
        tognr = (
            tognr.replace("Lyn+", "ICLPlus")
            .replace("IC-Lyntog", "ICL")
            .replace("InterCityLyn", "ICL")
            .replace("InterCity", "IC")
            .replace(" ", "")
        )
        plads_str = "%s_%s_%s" % (tognr, vogn, plads.replace(" ", "").replace(",", "-"))
        if typ:
            plads_str += "_%s" % typ
    fra = b.fra
    til = b.til
    if "Københavns" in fra or "CPH" in fra:
        fra = "CPHLufthavn"
    elif fra == "København":
        fra = "Kbh"
    if "Københavns" in til or "CPH" in til:
        til = "CPHLufthavn"
    elif til == "København":
        til = "Kbh"
    str_parts = [
        "%s-%02d-%02dT%02d%02d-%02d%02d"
        % (b.year, b.month, b.day, b.from_h, b.from_m, b.to_h, b.to_m),
        fra.split()[0],
        til.split()[0],
    ]
    if billet_str:
        str_parts.append(billet_str)
    if plads_str:
        str_parts.append(plads_str)
    return "_".join(str_parts)


def main() -> None:
    args = parser.parse_args()
    for f in args.filename:
        t = subprocess.check_output(("pdftotext", f, "-"))
        try:
            new_name = _fmt(parse_text(t)) + ".pdf"
        except (UnboundLocalError, NameError):
            raise
        except KeyboardInterrupt:
            print(f, "KeyboardInterrupt")
            raise
        except Exception:
            print(f, "EXCEPTION")
            traceback.print_exc()
            return
        if not os.path.exists(new_name):
            os.rename(f, new_name)


if __name__ == "__main__":
    main()
