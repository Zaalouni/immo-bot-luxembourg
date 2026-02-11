
cd /home/test/immo-bot-luxembourg
pkill -f "python.*main.py"

# Vider BDD pour test propre
rm listings.db 2>/dev/null

# Test bot complet
python3 main.py 
#--once



