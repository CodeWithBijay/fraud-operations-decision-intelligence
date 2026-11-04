"""Read database settings from Streamlit secrets (cloud) or environment variables (local)."""
p = "app/app.py"
s = open(p).read()
old = '''    user = os.environ.get("PGUSER", "fraud_app")
    pwd = os.environ.get("PGPASSWORD", "")
    host = os.environ.get("PGHOST", "localhost")
    db = os.environ.get("PGDATABASE", "fraud_risk_db")
    auth = f"{user}:{pwd}@" if pwd else f"{user}@"
    engine = create_engine(f"postgresql+psycopg2://{auth}{host}/{db}")
'''
new = '''    def setting(key, default=""):
        try:
            if key in st.secrets:  # Streamlit Cloud: values from the app's Secrets
                return str(st.secrets[key])
        except Exception:  # no secrets file when running locally
            pass
        return os.environ.get(key, default)

    url = URL.create("postgresql+psycopg2", username=setting("PGUSER", "fraud_app"),
                     password=setting("PGPASSWORD") or None, host=setting("PGHOST", "localhost"),
                     database=setting("PGDATABASE", "fraud_risk_db"))
    engine = create_engine(url, pool_pre_ping=True,
                           connect_args={"sslmode": setting("PGSSLMODE", "prefer")})
'''
if s.count(old) != 1:
    raise SystemExit("get_engine not found as expected. No changes saved.")
s = s.replace(old, new)
s = s.replace("from sqlalchemy import create_engine, text", "from sqlalchemy import URL, create_engine, text", 1)
open(p, "w").write(s)
print("Applied cloud database fix to", p)
