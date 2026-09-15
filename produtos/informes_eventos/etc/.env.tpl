# Template do `.env` do projeto — commitável: contém apenas refs 1Password.
#
# Uso preferido (nada toca o disco):
#   op run --env-file=etc/.env.tpl -- python seu_script.py
#
# Alternativa, materializa um .env real:
#   op inject -i etc/.env.tpl -o etc/.env
#
# Requer o app do 1Password com a integração de CLI ativa.

# FRED API (https://fred.stlouisfed.org/docs/api/api_key.html)
FRED_API_KEY=op://dev/FRED/credential
