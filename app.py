from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'bovimonitor_agro_secret'  # Necessário para validações e mensagens Flash

# Banco de dados em memória para simulação
historico_vacinas = []

def calcular_status(data_reforco_str):
    """Calcula se a revacinação está Em dia (verde), Próxima (amarelo) ou Vencida (vermelho)."""
    hoje = datetime.now().date()
    data_reforco = datetime.strptime(data_reforco_str, '%Y-%m-%d').date()
    dias_restantes = (data_reforco - hoje).days

    if dias_restantes < 0:
        return 'status-vencida', 'Vencida/Pendente'
    elif dias_restantes <= 30:
        return 'status-proxima', f'Próxima ({dias_restantes} dias)'
    else:
        return 'status-em-dia', 'Em Dia'

@app.route('/')
def index():
    # Indicators/Estatísticas do Dashboard
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    vacinados_mes = 0
    total_doses_ml = 0.0
    custo_total_lote = 0.0
    alertas_reforco = 0

    for reg in historico_vacinas:
        dt_app = datetime.strptime(reg['data_aplicacao_raw'], '%Y-%m-%d')
        if dt_app.month == mes_atual and dt_app.year == ano_atual:
            vacinados_mes += 1
            total_doses_ml += reg['dosagem_ml']

        custo_total_lote += reg['custo_total_animal']

        # Alerta se estiver vencida ou faltarem menos de 30 dias para reforço
        status_class, _ = calcular_status(reg['data_reforco_raw'])
        if status_class in ['status-vencida', 'status-proxima']:
            alertas_reforco += 1

    metrics = {
        'vacinados_mes': vacinados_mes,
        'total_doses_ml': round(total_doses_ml, 2),
        'custo_lote': round(custo_total_lote, 2),
        'alertas_reforco': alertas_reforco
    }

    return render_template('index.html', metrics=metrics)

@app.route('/manejo', methods=['GET', 'POST'])
def registrar_manejo():
    if request.method == 'POST':
        brinco = request.form.get('brinco', '').strip()
        peso_str = request.form.get('peso', '0')
        vacina = request.form.get('vacina', '').strip()
        data_aplicacao_str = request.form.get('data_aplicacao', '')
        custo_ml_str = request.form.get('custo_ml', '0')

        # --- VALIDAÇÕES SANITÁRIAS ---
        if not brinco or not vacina or not data_aplicacao_str:
            flash('Erro: Todos os campos obrigatórios (Brinco, Vacina e Data) devem ser preenchidos!', 'danger')
            return redirect(url_for('registrar_manejo'))

        try:
            peso_kg = float(peso_str)
            custo_ml = float(custo_ml_str)
            if peso_kg <= 0 or custo_ml < 0:
                flash('Erro: O peso deve ser maior que zero e o custo não pode ser negativo!', 'danger')
                return redirect(url_for('registrar_manejo'))
        except ValueError:
            flash('Erro: Insira valores numéricos válidos para peso e custo.', 'danger')
            return redirect(url_for('registrar_manejo'))

        # --- REGRAS DE NEGÓCIO AGRO ---
        # 1. Dosagem: 1 mL para cada 50 kg de peso vivo
        dosagem_ml = round(peso_kg / 50.0, 2)

        # 2. Custo individual
        custo_total_animal = round(dosagem_ml * custo_ml, 2)

        # 3. Ciclo de Reforço (180 dias / 6 meses)
        dt_aplicacao = datetime.strptime(data_aplicacao_str, '%Y-%m-%d')
        dt_reforco = dt_aplicacao + timedelta(days=180)

        registro = {
            'brinco': brinco,
            'peso_kg': peso_kg,
            'vacina': vacina,
            'dosagem_ml': dosagem_ml,
            'custo_ml': custo_ml,
            'custo_total_animal': custo_total_animal,
            'data_aplicacao_fmt': dt_aplicacao.strftime('%d/%m/%Y'),
            'data_aplicacao_raw': data_aplicacao_str,
            'data_reforco_fmt': dt_reforco.strftime('%d/%m/%Y'),
            'data_reforco_raw': dt_reforco.strftime('%Y-%m-%d')
        }

        historico_vacinas.append(registro)
        flash('Registro de manejo sanitário cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_historico'))

    return render_template('manejo.html')

@app.route('/historico')
def listar_historico():
    # Processa os status sanitários para exibição na tabela
    historico_processado = []
    for reg in historico_vacinas:
        status_class, status_label = calcular_status(reg['data_reforco_raw'])
        item = reg.copy()
        item['status_class'] = status_class
        item['status_label'] = status_label
        historico_processado.append(item)

    return render_template('historico.html', registros=historico_processado)

if __name__ == '__main__':
    app.run(debug=True)