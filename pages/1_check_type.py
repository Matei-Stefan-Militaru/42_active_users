"""
check_unique_states.py

Recorre TODA la cursus_users de un campus (sin filtrar por KEEP_GRADES,
a diferencia de la app Streamlit) y te muestra todos los valores únicos
reales que aparecen en la API para: grade, kind, active?, y combinaciones
end_at/blackholed_at. Sirve para verificar que tu filtro KEEP_GRADES no
se está comiendo estados que no conoces (ej: "Freshman", "Member", etc.)

USO:
    export API42_CLIENT_ID="..."
    export API42_CLIENT_SECRET="..."
    python check_unique_states.py --campus 46 --cursus 21

Si no pasas --campus, recorre TODOS los campus (más lento, útil para
un chequeo global de una vez).
"""

import os
import sys
import time
import argparse
import requests
from collections import Counter

def get_credentials():
    cid = os.environ.get("API42_CLIENT_ID")
    csec = os.environ.get("API42_CLIENT_SECRET")
    if not cid or not csec:
        # fallback: intenta leer de .streamlit/secrets.toml si existe
        try:
            import toml
            secrets = toml.load(".streamlit/secrets.toml")
            cid = cid or secrets["api42"]["client_id"]
            csec = csec or secrets["api42"]["client_secret"]
        except Exception:
            pass
    if not cid or not csec:
        sys.exit(
            "❌ Faltan credenciales. Define API42_CLIENT_ID y API42_CLIENT_SECRET "
            "como variables de entorno, o ten un .streamlit/secrets.toml válido."
        )
    return cid, csec


def get_token(cid, csec):
    resp = requests.post(
        "https://api.intra.42.fr/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": csec,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def api_get(url, headers, cid, csec):
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code == 401:
        headers["Authorization"] = f"Bearer {get_token(cid, csec)}"
        resp = requests.get(url, headers=headers, timeout=20)
    return resp, headers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campus", type=int, default=None, help="ID de campus (omite para todos)")
    parser.add_argument("--cursus", type=int, default=21, help="ID de cursus (default 21)")
    parser.add_argument("--max-pages", type=int, default=500)
    args = parser.parse_args()

    cid, csec = get_credentials()
    headers = {"Authorization": f"Bearer {get_token(cid, csec)}"}

    grade_counter = Counter()
    kind_counter = Counter()
    active_counter = Counter()
    end_bh_counter = Counter()      # combinación end_at / blackholed_at presentes o no
    raw_grade_empty_examples = []   # logins donde grade viene vacío, para inspeccionar

    total = 0
    page = 1
    base = f"https://api.intra.42.fr/v2/cursus/{args.cursus}/cursus_users"

    while page <= args.max_pages:
        url = f"{base}?page[size]=100&page[number]={page}&sort=-updated_at"
        if args.campus:
            url = f"{base}?filter[campus_id]={args.campus}&page[size]=100&page[number]={page}&sort=-updated_at"

        resp, headers = api_get(url, headers, cid, csec)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            print(f"⏳ Rate limit, esperando {wait}s...")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            print(f"❌ Error {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        if not data:
            break

        for cu in data:
            user = cu.get("user") or {}
            if not user:
                continue
            total += 1

            raw_grade = (cu.get("grade") or "").strip()
            grade_counter[raw_grade if raw_grade else "(vacío/null)"] += 1

            kind_counter[user.get("kind", "(sin kind)")] += 1

            active_counter[user.get("active?", "(sin campo)")] += 1

            has_end = bool(cu.get("end_at"))
            has_bh = bool(cu.get("blackholed_at"))
            end_bh_counter[f"end_at={has_end} / blackholed_at={has_bh}"] += 1

            if not raw_grade and len(raw_grade_empty_examples) < 10:
                raw_grade_empty_examples.append(user.get("login", "?"))

        print(f"📄 Página {page} · acumulado: {total}")

        if len(data) < 100:
            break
        page += 1

    print("\n" + "=" * 60)
    print(f"TOTAL registros analizados: {total}")
    print("=" * 60)

    print("\n🎓 VALORES ÚNICOS DE 'grade' (crudo, tal cual lo da la API):")
    for val, count in grade_counter.most_common():
        print(f"   {val!r:20} → {count}")

    print("\n👤 VALORES ÚNICOS DE 'kind':")
    for val, count in kind_counter.most_common():
        print(f"   {val!r:20} → {count}")

    print("\n🟢 VALORES ÚNICOS DE 'active?':")
    for val, count in active_counter.most_common():
        print(f"   {val!r:20} → {count}")

    print("\n🕳️  COMBINACIONES end_at / blackholed_at:")
    for val, count in end_bh_counter.most_common():
        print(f"   {val:35} → {count}")

    if raw_grade_empty_examples:
        print(f"\n⚠️  Ejemplos de logins con grade vacío (útil para revisar tu detect_grade): {raw_grade_empty_examples}")

    print("\n💡 Compara los valores de 'grade' de arriba contra tu KEEP_GRADES actual:")
    print("   KEEP_GRADES = {'Cadet', 'Outercore', 'Transcender', 'Alumni', 'Blackholed'}")
    missing = set(grade_counter.keys()) - {"Cadet", "Outercore", "Transcender", "Alumni", "Blackholed", "(vacío/null)"}
    if missing:
        print(f"   🚨 Valores que tu filtro actual estaría IGNORANDO: {missing}")
    else:
        print("   ✅ No hay valores de grade fuera de tu KEEP_GRADES (aparte de vacíos).")


if __name__ == "__main__":
    main()
