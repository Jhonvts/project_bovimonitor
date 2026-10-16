from datetime import datetime, timedelta
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = 'bovimonitor_agro_secret'

# Bancos de dados em memória para simulação
historico_vacinas = []
lista_vacinas = []  # Armazena o cadastro geral de vacinas/medicamentos
lista_lotes = []    # Armazena o registro de lotes de gado

# Usuário de exemplo simulado para o perfil
usuario_atual = {
    'nome': 'Produtor Rural',
    'email': 'produtor@bovimonitor.com',
    'telefone': '(69) 99999-9999'
}

propriedade_atual = {
    'nome': 'Fazenda Boa Esperança',
    'localizacao': 'Ariquemes - RO',
    'area': 150
}


def calcular_status(data_reforco_str):
    """Calcula se a revacinação está:
    Em dia (verde), Próxima (amarelo) ou Vencida (vermelho).
    """
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
    # Indicadores/Estatísticas do Dashboard
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

        # Alerta se estiver vencida ou faltarem menos de 30 dias para o reforço
        status_class, _ = calcular_status(reg['data_reforco_raw'])

        if status_class in ['status-vencida', 'status-proxima']:
            alertas_reforco += 1

    metrics = {
        'vacinados_mes': vacinados_mes,
        'total_doses_ml': round(total_doses_ml, 2),
        'custo_lote': round(custo_total_lote, 2),
        'alertas_reforco': alertas_reforco,
    }

    return render_template('dashboard.html', metrics=metrics)


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
            flash(
                'Erro: Todos os campos obrigatórios (Brinco, Vacina e Data) devem ser preenchidos!',
                'danger',
            )
            return redirect(url_for('registrar_manejo'))

        try:
            peso_kg = float(peso_str)
            custo_ml = float(custo_ml_str)

            if peso_kg <= 0 or custo_ml < 0:
                flash(
                    'Erro: O peso deve ser maior que zero e o custo não pode ser negativo!',
                    'danger',
                )
                return redirect(url_for('registrar_manejo'))

        except ValueError:
            flash(
                'Erro: Insira valores numéricos válidos para peso e custo.', 'danger'
            )
            return redirect(url_for('registrar_manejo'))

        # --- REGRAS DE NEGÓCIO AGRO ---
        dosagem_ml = round(peso_kg / 50.0, 2)
        custo_total_animal = round(dosagem_ml * custo_ml, 2)

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
            'data_reforco_raw': dt_reforco.strftime('%Y-%m-%d'),
        }

        historico_vacinas.append(registro)

        flash('Registro de manejo sanitário cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_historico'))

    return render_template('cadastroManejoVacinas.html')


@app.route('/historico')
def listar_historico():
    historico_processado = []

    for reg in historico_vacinas:
        status_class, status_label = calcular_status(reg['data_reforco_raw'])
        item = reg.copy()
        item['status_class'] = status_class
        item['status_label'] = status_label
        historico_processado.append(item)

    return render_template(
        'historico_de_Vacinas.html', registros=historico_processado
    )


# --- ROTAS DE VACINAS / MEDICAMENTOS ---
@app.route('/vacina/cadastrar', methods=['GET', 'POST'])
def cadastro_vacina():
    if request.method == 'POST':
        nova_vacina = {
            'id': len(lista_vacinas) + 1,
            'nome': request.form.get('nome'),
            'tipo': request.form.get('tipo'),
            'dias_carencia': request.form.get('dias_carencia'),
            'obrigatoria': request.form.get('obrigatoria')
        }
        lista_vacinas.append(nova_vacina)
        flash('Vacina/Medicamento cadastrado com sucesso!', 'success')
        return redirect(url_for('historico_vacinas'))
    return render_template('cadastrar_vacina.html')


@app.route('/vacinas')
def historico_vacinas():
    return render_template('historico_vacinas.html', vacinas=lista_vacinas)


@app.route('/vacina/editar/<int:id>', methods=['GET', 'POST'])
def editar_vacina(id):
    vacina = next((v for v in lista_vacinas if v['id'] == id), None)
    if not vacina:
        flash('Vacina não encontrada!', 'danger')
        return redirect(url_for('historico_vacinas'))

    if request.method == 'POST':
        vacina['nome'] = request.form.get('nome')
        vacina['tipo'] = request.form.get('tipo')
        vacina['dias_carencia'] = request.form.get('dias_carencia')
        vacina['obrigatoria'] = request.form.get('obrigatoria')
        flash('Vacina atualizada com sucesso!', 'success')
        return redirect(url_for('historico_vacinas'))

    return render_template('editar_vacina.html', vacina=vacina)


@app.route('/vacina/deletar/<int:id>', methods=['POST'])
def deletar_vacina(id):
    global lista_vacinas
    lista_vacinas = [v for v in lista_vacinas if v['id'] != id]
    flash('Vacina removida com sucesso!', 'success')
    return redirect(url_for('historico_vacinas'))


# --- ROTAS DE PERFIL E AUTENTICAÇÃO ---
@app.route('/perfil')
def perfil():
    return render_template('perfil.html', usuario=usuario_atual, propriedade=propriedade_atual)


@app.route('/perfil/editar', methods=['GET', 'POST'])
def editar_perfil():
    if request.method == 'POST':
        usuario_atual['nome'] = request.form.get('nome')
        usuario_atual['telefone'] = request.form.get('telefone')
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil'))
    
    return render_template('editar_perfil.html', usuario=usuario_atual)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        # Simulação de verificação de login
        flash('Login realizado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))


# --- ROTAS DE LOTES ---
@app.route('/lotes', methods=['GET', 'POST'])
def registro_lotes():
    if request.method == 'POST':
        novo_lote = {
            'id': len(lista_lotes) + 1,
            'nome': request.form.get('nome'),
            'quantidade': request.form.get('quantidade'),
            'tendas': request.form.get('tendas'),
            'status': request.form.get('status')
        }
        lista_lotes.append(novo_lote)
        flash('Lote cadastrado com sucesso!', 'success')
        return redirect(url_for('registro_lotes'))
    return render_template('registro_lotes.html', lotes=lista_lotes)


@app.route('/lotes/editar/<int:id>', methods=['GET', 'POST'])
def editar_lote(id):
    lote = next((l for l in lista_lotes if l['id'] == id), None)
    if not lote:
        flash('Lote não encontrado!', 'danger')
        return redirect(url_for('registro_lotes'))

    if request.method == 'POST':
        lote['nome'] = request.form.get('nome')
        lote['quantidade'] = request.form.get('quantidade')
        lote['tendas'] = request.form.get('tendas')
        lote['status'] = request.form.get('status')
        flash('Lote atualizado com sucesso!', 'success')
        return redirect(url_for('registro_lotes'))

    return render_template('editar_lote.html', lote=lote)


@app.route('/lotes/excluir/<int:id>', methods=['POST'])
def excluir_lote(id):
    global lista_lotes
    lista_lotes = [l for l in lista_lotes if l['id'] != id]
    flash('Lote excluído com sucesso!', 'success')
    return redirect(url_for('registro_lotes'))


if __name__ == '__main__':
    app.run(debug=True)