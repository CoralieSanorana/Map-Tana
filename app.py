from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Route pour afficher la page principale
@app.route('/')
def index():
    return render_template('index.html')

# Route pour la logique d'estimation (ton projet Python)
@app.route('/estimer', methods=['POST'])
def estimer():
    data = request.json
    # --- TA LOGIQUE PYTHON ICI ---
    prix_base = 150000
    
    # Exemple simple de calcul
    if data['accessibilite'] == 'voiture':
        prix_base *= 1.2
    if data['papier'] == 'titre borne':
        prix_base *= 1.3
        
    return jsonify({"prix_estime": prix_base})

if __name__ == '__main__':
    app.run(debug=True)