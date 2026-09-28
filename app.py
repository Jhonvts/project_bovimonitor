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
    
    if vacina == "Vermífugo/Antiparasitário":
        dosagem = round(peso / 50.0, 2)  # 1 mL para cada 50kg
    else:
        dosagem = 2.0  # Dose fixa padrão para vacinas
        
    custo_total = round(dosagem * custo_ml, 2)
    data_reforco = data_ap + timedelta(days=180)
    
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
    # Redireciona para o Dashboard principal
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Calcula as métricas reais com base nos registros salvos
    mes_atual = datetime.now().month
    vacinados_mes = sum(1 for r in historico_vacinas if datetime.strptime(r['data_aplicacao_raw'], "%Y-%m-%d").month == mes_atual)
    total_doses_ml = sum(r['dosagem_ml'] for r in historico_vacinas)
    custo_lote = sum(r['custo_total_animal'] for r in historico_vacinas)
    alertas_reforco = sum(1 for r in historico_vacinas if r['status_label'] == "Atenção (Reforço)")

    metrics = {
        "vacinados_mes": vacinados_mes,
        "total_doses_ml": total_doses_ml,
        "custo_lote": custo_lote,
        "alertas_reforco": alertas_reforco
    }
    return render_template('dashboard.html', metrics=metrics)

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

@app.route('/deletar/<int:id>', methods=['POST'])
def deletar_manejo(id):
    global historico_vacinas
    historico_vacinas = [r for r in historico_vacinas if r['id'] != id]
    return redirect(url_for('historico'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_manejo(id):
    registro = next((r for r in historico_vacinas if r['id'] == id), None)
    if not registro:
        return redirect(url_for('historico'))
        
    if request.method == 'POST':
        registro['brinco'] = request.form['brinco']
        registro['vacina'] = request.form['vacina']
        
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