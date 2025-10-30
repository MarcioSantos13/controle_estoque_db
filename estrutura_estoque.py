#!/usr/bin/env python3
"""
Sistema de Verificação da Estrutura do Banco de Dados - Controle Patrimonial
Autor: Sistema CEAD
Descrição: Verifica a estrutura completa do banco de dados SQLite
"""

import sqlite3
import os
import sys
from datetime import datetime
import pandas as pd

class VerificadorEstruturaBanco:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.estrutura = {}
        
    def conectar(self):
        """Conecta ao banco de dados"""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Banco de dados não encontrado: {self.db_path}")
                return False
                
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"✅ Conectado ao banco: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def desconectar(self):
        """Desconecta do banco de dados"""
        if self.conn:
            self.conn.close()
            print("✅ Conexão fechada")
    
    def obter_tabelas(self):
        """Obtém lista de todas as tabelas"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = [row[0] for row in cursor.fetchall()]
            return tabelas
        except Exception as e:
            print(f"❌ Erro ao obter tabelas: {e}")
            return []
    
    def obter_estrutura_tabela(self, tabela_nome):
        """Obtém estrutura completa de uma tabela"""
        try:
            cursor = self.conn.cursor()
            
            # Informações das colunas
            cursor.execute(f"PRAGMA table_info({tabela_nome})")
            colunas = cursor.fetchall()
            
            # Índices
            cursor.execute(f"PRAGMA index_list({tabela_nome})")
            indices = cursor.fetchall()
            
            # Chaves estrangeiras
            cursor.execute(f"PRAGMA foreign_key_list({tabela_nome})")
            foreign_keys = cursor.fetchall()
            
            # Estatísticas básicas
            cursor.execute(f"SELECT COUNT(*) as total FROM {tabela_nome}")
            total_registros = cursor.fetchone()[0]
            
            return {
                'colunas': colunas,
                'indices': indices,
                'foreign_keys': foreign_keys,
                'total_registros': total_registros
            }
        except Exception as e:
            print(f"❌ Erro ao obter estrutura da tabela {tabela_nome}: {e}")
            return None
    
    def obter_amostra_dados(self, tabela_nome, limite=5):
        """Obtém amostra de dados da tabela"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {tabela_nome} LIMIT {limite}")
            colunas = [desc[0] for desc in cursor.description]
            dados = cursor.fetchall()
            return colunas, dados
        except Exception as e:
            print(f"❌ Erro ao obter amostra de {tabela_nome}: {e}")
            return [], []
    
    def verificar_integridade(self):
        """Verifica integridade do banco de dados"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            resultado = cursor.fetchone()
            return resultado[0]
        except Exception as e:
            return f"Erro: {e}"
    
    def gerar_relatorio_completo(self):
        """Gera relatório completo da estrutura do banco"""
        print("=" * 80)
        print("📊 RELATÓRIO COMPLETO DA ESTRUTURA DO BANCO DE DADOS")
        print("=" * 80)
        print(f"📁 Banco: {self.db_path}")
        print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📏 Tamanho: {os.path.getsize(self.db_path) / 1024 / 1024:.2f} MB")
        print()
        
        # Verificar integridade
        integridade = self.verificar_integridade()
        print(f"🔍 Integridade do banco: {integridade}")
        print()
        
        # Obter tabelas
        tabelas = self.obter_tabelas()
        print(f"📋 TABELAS ENCONTRADAS ({len(tabelas)}):")
        print("-" * 40)
        
        for tabela in tabelas:
            estrutura = self.obter_estrutura_tabela(tabela)
            if estrutura:
                print(f"\n🏷️  TABELA: {tabela}")
                print(f"   📊 Total de registros: {estrutura['total_registros']:,}")
                
                # Colunas
                print("   📝 COLUNAS:")
                for coluna in estrutura['colunas']:
                    pk = " 🔑" if coluna[5] == 1 else ""
                    nullable = " NOT NULL" if not coluna[3] else ""
                    default = f" DEFAULT {coluna[4]}" if coluna[4] else ""
                    print(f"      • {coluna[1]} ({coluna[2]}){nullable}{default}{pk}")
                
                # Índices
                if estrutura['indices']:
                    print("   📑 ÍNDICES:")
                    for idx in estrutura['indices']:
                        unique = " UNIQUE" if idx[2] else ""
                        print(f"      • {idx[1]}{unique}")
                
                # Chaves estrangeiras
                if estrutura['foreign_keys']:
                    print("   🔗 CHAVES ESTRANGEIRAS:")
                    for fk in estrutura['foreign_keys']:
                        print(f"      • {fk[3]} → {fk[2]}.{fk[4]}")
                
                # Amostra de dados
                if estrutura['total_registros'] > 0:
                    colunas, dados = self.obter_amostra_dados(tabela)
                    if dados:
                        print(f"   📋 AMOSTRA DE DADOS (primeiros {len(dados)} registros):")
                        # Mostrar cabeçalho
                        header = " | ".join(f"{col:<15}" for col in colunas[:4])  # Mostrar até 4 colunas
                        print(f"      {header}")
                        print(f"      {'-' * len(header)}")
                        
                        # Mostrar dados
                        for linha in dados:
                            valores = []
                            for i, valor in enumerate(linha):
                                if i >= 4:  # Limitar a 4 colunas na amostra
                                    break
                                if valor is None:
                                    valores.append("NULL")
                                else:
                                    valor_str = str(valor)
                                    if len(valor_str) > 15:
                                        valor_str = valor_str[:12] + "..."
                                    valores.append(f"{valor_str:<15}")
                            print(f"      {' | '.join(valores)}")
                
                print("-" * 40)
    
    def verificar_estrutura_bens(self):
        """Verificação específica da tabela bens"""
        print("\n" + "=" * 60)
        print("🔍 VERIFICAÇÃO ESPECÍFICA - TABELA BENS")
        print("=" * 60)
        
        estrutura = self.obter_estrutura_tabela('bens')
        if not estrutura:
            print("❌ Tabela 'bens' não encontrada!")
            return False
        
        print("✅ Tabela 'bens' encontrada")
        print(f"📊 Total de registros: {estrutura['total_registros']:,}")
        
        # Verificar colunas obrigatórias
        colunas_obrigatorias = ['numero', 'nome', 'situacao']
        colunas_encontradas = [col[1] for col in estrutura['colunas']]
        
        print("\n📋 COLUNAS OBRIGATÓRIAS:")
        for coluna in colunas_obrigatorias:
            if coluna in colunas_encontradas:
                print(f"   ✅ {coluna}")
            else:
                print(f"   ❌ {coluna} - FALTANDO!")
        
        # Verificar colunas adicionais
        colunas_adicionais = ['localizacao', 'responsavel', 'data_ultima_vistoria', 
                             'data_vistoria_atual', 'auditor', 'observacoes']
        
        print("\n📋 COLUNAS ADICIONAIS:")
        for coluna in colunas_adicionais:
            if coluna in colunas_encontradas:
                print(f"   ✅ {coluna}")
            else:
                print(f"   ⚠️  {coluna} - Não encontrada")
        
        # Estatísticas de situação
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT situacao, COUNT(*) as total FROM bens GROUP BY situacao")
            situacoes = cursor.fetchall()
            
            print("\n📈 DISTRIBUIÇÃO POR SITUAÇÃO:")
            for situacao, total in situacoes:
                situacao_str = situacao if situacao else 'NULL/VAZIO'
                print(f"   • {situacao_str}: {total:,} registros")
        except Exception as e:
            print(f"   ⚠️  Erro ao obter distribuição: {e}")
        
        # Verificar dados problemáticos
        print("\n🔍 VERIFICAÇÃO DE DADOS PROBLEMÁTICOS:")
        
        # Registros sem número
        cursor.execute("SELECT COUNT(*) FROM bens WHERE numero IS NULL OR numero = ''")
        sem_numero = cursor.fetchone()[0]
        print(f"   • Registros sem número: {sem_numero}")
        
        # Registros sem nome
        cursor.execute("SELECT COUNT(*) FROM bens WHERE nome IS NULL OR nome = ''")
        sem_nome = cursor.fetchone()[0]
        print(f"   • Registros sem nome: {sem_nome}")
        
        # Números duplicados
        cursor.execute("""
            SELECT numero, COUNT(*) as count 
            FROM bens 
            GROUP BY numero 
            HAVING COUNT(*) > 1
        """)
        duplicados = cursor.fetchall()
        print(f"   • Números duplicados: {len(duplicados)}")
        if duplicados:
            for numero, count in duplicados[:5]:  # Mostrar apenas os 5 primeiros
                print(f"      - {numero}: {count} ocorrências")
        
        return True
    
    def exportar_para_excel(self, arquivo_saida=None):
        """Exporta estrutura para Excel"""
        if not arquivo_saida:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_saida = f"estrutura_banco_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
                
                # Worksheet de tabelas
                tabelas = self.obter_tabelas()
                dados_tabelas = []
                
                for tabela in tabelas:
                    estrutura = self.obter_estrutura_tabela(tabela)
                    if estrutura:
                        dados_tabelas.append({
                            'Tabela': tabela,
                            'Registros': estrutura['total_registros'],
                            'Colunas': len(estrutura['colunas']),
                            'Índices': len(estrutura['indices'])
                        })
                
                if dados_tabelas:
                    df_tabelas = pd.DataFrame(dados_tabelas)
                    df_tabelas.to_excel(writer, sheet_name='Tabelas', index=False)
                
                # Worksheet de colunas
                dados_colunas = []
                for tabela in tabelas:
                    estrutura = self.obter_estrutura_tabela(tabela)
                    if estrutura:
                        for coluna in estrutura['colunas']:
                            dados_colunas.append({
                                'Tabela': tabela,
                                'Coluna': coluna[1],
                                'Tipo': coluna[2],
                                'Pode ser Nulo': 'NÃO' if not coluna[3] else 'SIM',
                                'Valor Padrão': coluna[4] or '',
                                'Chave Primária': 'SIM' if coluna[5] == 1 else 'NÃO'
                            })
                
                if dados_colunas:
                    df_colunas = pd.DataFrame(dados_colunas)
                    df_colunas.to_excel(writer, sheet_name='Colunas', index=False)
                
                # Worksheet de amostra de dados da tabela bens
                if 'bens' in tabelas:
                    colunas, dados = self.obter_amostra_dados('bens', 100)  # 100 registros
                    if dados:
                        df_amostra = pd.DataFrame(dados, columns=colunas)
                        df_amostra.to_excel(writer, sheet_name='Amostra_Bens', index=False)
                
                print(f"✅ Relatório exportado para: {arquivo_saida}")
                return arquivo_saida
                
        except Exception as e:
            print(f"❌ Erro ao exportar para Excel: {e}")
            return None

def main():
    """Função principal"""
    # Configurar caminho do banco
    db_path = "relatorios/controle_patrimonial.db"
    
    # Verificar se o banco existe
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        print("📂 Diretório atual:", os.getcwd())
        print("📂 Conteúdo do diretório:")
        for item in os.listdir():
            print(f"   - {item}")
        return
    
    # Criar verificador
    verificador = VerificadorEstruturaBanco(db_path)
    
    # Conectar
    if not verificador.conectar():
        return
    
    try:
        # Menu interativo
        while True:
            print("\n" + "=" * 60)
            print("🔧 VERIFICADOR DE ESTRUTURA DO BANCO DE DADOS")
            print("=" * 60)
            print("1. 📊 Relatório completo da estrutura")
            print("2. 🔍 Verificação específica da tabela bens")
            print("3. 📈 Estatísticas gerais")
            print("4. 💾 Exportar para Excel")
            print("5. 🚪 Sair")
            print("-" * 60)
            
            opcao = input("🎯 Escolha uma opção (1-5): ").strip()
            
            if opcao == '1':
                verificador.gerar_relatorio_completo()
                
            elif opcao == '2':
                verificador.verificar_estrutura_bens()
                
            elif opcao == '3':
                print("\n📈 ESTATÍSTICAS GERAIS:")
                print("-" * 30)
                tabelas = verificador.obter_tabelas()
                print(f"• Total de tabelas: {len(tabelas)}")
                
                total_registros = 0
                for tabela in tabelas:
                    estrutura = verificador.obter_estrutura_tabela(tabela)
                    if estrutura:
                        total_registros += estrutura['total_registros']
                        print(f"• {tabela}: {estrutura['total_registros']:,} registros")
                
                print(f"• TOTAL GERAL: {total_registros:,} registros")
                
            elif opcao == '4':
                arquivo = verificador.exportar_para_excel()
                if arquivo:
                    print(f"✅ Exportação concluída: {arquivo}")
                    
            elif opcao == '5':
                print("👋 Saindo...")
                break
                
            else:
                print("❌ Opção inválida!")
            
            input("\n📝 Pressione Enter para continuar...")
            
    finally:
        verificador.desconectar()

if __name__ == "__main__":
    main()