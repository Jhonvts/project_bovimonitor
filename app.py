from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)

# Lista simulando o banco de dados em memória
historico_vacinas = []
contador_id = 1

def calcular_dosagem_e_reforco(peso, vacina, custo_ml, data_aplicacao_str):
    """Calcula dosagem, custos, datas e status sanitário."""
    peso = float(peso)
    custo_ml = float(custo_ml)
    data_ap = datetime.strptime(data_aplicacao_str, "%Y-%m-%d")
    
    # Cálculo simples de dosagem dependendo do tipo (exemplo genérico)
    if vacina == "Vermífugo/Antiparasitário":
        dosagem = round(peso / 50.0, 2)  # 1 mL para cada 50kg
    else:
        dosagem = 2.0  # Dose fixa padrão para vacinas
        
    custo_total = round(dosagem * custo_ml, 2)
    
    # Data de reforço (ex: 180 dias após aplicação)
    data_reforco = data_ap + timedelta(days=180)
    
    # Cálculo de status
    hoje = datetime.now()
    dias_restantes = (data_reforco - hoje).days
    
    if dias_restantes < 0:
        status_label = "Vencido"
        status_class = "badge-danger"
    elif dias_restantes <= 30:
        status_label = "Atenção (Reforço)"
        status_class = "badge-warning"
    else:
        status_label = "Em Dia"
        status_class = "badge-success"

    return {
        "peso_kg": peso,
        "dosagem_ml": dosagem,
        "custo_ml": custo_ml,
        "custo_total_animal": custo_total,
        "data_aplicacao_raw": data_aplicacao_str,
        "data_aplicacao_fmt": data_ap.strftime("%d/%m/%Y"),
        "data_reforco_fmt": data_reforco.strftime("%d/%m/%Y"),
        "status_label": status_label,
        "status_class": status_class
    }

@app.route('/')
def index():
    return redirect(url_for('historico'))

@app.route('/historico')
def historico():
    return render_template('historico.html', registros=historico_vacinas)

@app.route('/registrar', methods=['GET', 'POST'])
def registrar_manejo():
    global contador_id
    if request.method == 'POST':
        brinco = request.form['brinco']
        peso = request.form['peso']
        vacina = request.form['vacina']
        custo_ml = request.form['custo_ml']
        data_aplicacao = request.form['data_aplicacao']
        
        calculados = calcular_dosagem_e_reforco(peso, vacina, custo_ml, data_aplicacao)
        
        registro = {
            "id": contador_id,
            "brinco": brinco,
            "vacina": vacina,
            **calculados
        }
        
        historico_vacinas.append(registro)
        contador_id += 1
        
        return redirect(url_for('historico'))
        
    return render_template('manejo.html')

# ROTAS DE EDIÇÃO E EXCLUSÃO
@app.route('/deletar/<int:id>', methods=['POST'])
def deletar_manejo(id):
    global historico_vacinas
    historico_vacinas = [r for r in historico_vacinas if r['id'] != id]
    return redirect(url_for('historico'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_manejo(id):
    # Procura o registro pelo ID
    registro = next((r for r in historico_vacinas if r['id'] == id), None)
    if not registro:
        return redirect(url_for('historico'))
        
    if request.method == 'POST':
        registro['brinco'] = request.form['brinco']
        registro['vacina'] = request.form['vacina']
        
        # Recalcula com base nos novos valores informados
        calculados = calcular_dosagem_e_reforco(
            request.form['peso'],
            request.form['vacina'],
            request.form['custo_ml'],
            request.form['data_aplicacao']
        )
        registro.update(calculados)
        
        return redirect(url_for('historico'))
        
    return render_template('editar_manejo.html', registro=registro)

if __name__ == '__main__':
    app.run(debug=True)