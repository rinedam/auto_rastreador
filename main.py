import sys
import threading
import logging
from pathlib import Path
import json
import time  # Import específico para time.sleep()

from datetime import datetime  # Import específico para datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QTextEdit, 
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QProgressBar, QMessageBox, QFrame,
    QTimeEdit, QDialog, QDialogButtonBox, 
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# Importar o código original
import atualizacao_ssw as ssw_updater

# Configuração de diretóriosc
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Handler personalizado para capturar logs e enviá-los para a interface
class QTextEditLogger(logging.Handler, QObject):
    log_signal = pyqtSignal(str, int)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        # Formato mais detalhado para incluir todos os logs
        self.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                            datefmt='%H:%M:%S')
        )

    def emit(self, record):
        msg = self.format(record)
        # Emite o sinal com a mensagem formatada e o nível do log
        self.log_signal.emit(msg, record.levelno)

class SSWUpdaterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.schedules = []
        self.initUI()
        self.setupLogging()
        self.setup_schedule_timer()
        
        # Mensagem inicial de log para informar que o sistema está pronto
        logging.info("Sistema iniciado e pronto para uso.")

    def log_direto(self, msg):
        # Define cor azul para destacar mensagens importantes
        self.log_area.setTextColor(QColor(0, 70, 140))
        self.log_area.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")
        # Rolagem automática para a última linha
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        
    def initUI(self):
        self.setWindowTitle('Atualizador de Sistema SSW')
        self.setMinimumSize(800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Título
        title_label = QLabel("Sistema de Atualização SSW")
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Informações do aplicativo
        info_label = QLabel("Este aplicativo atualiza o sistema SSW com as localizações dos veículos.")
        info_label.setFont(QFont('Arial', 10))
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Status
        self.status_label = QLabel("Pronto para iniciar")
        self.status_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminado
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Área de log
        log_label = QLabel("Log de execução:")
        log_label.setFont(QFont('Arial', 10, QFont.Bold))
        main_layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont('Consolas', 9))
        self.log_area.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_area)
        
        # Botões
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.start_button = QPushButton("Iniciar Atualização")
        self.start_button.setFont(QFont('Arial', 10))
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_update)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Parar")
        self.stop_button.setFont(QFont('Arial', 10))
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_update)
        button_layout.addWidget(self.stop_button)
        
        self.exit_button = QPushButton("Sair")
        self.exit_button.setFont(QFont('Arial', 10))
        self.exit_button.setMinimumHeight(40)
        self.exit_button.clicked.connect(self.close_application)
        button_layout.addWidget(self.exit_button)
        
        # Adicione o botão de configurar horários
        self.schedule_button = QPushButton("Configurar Horários")
        self.schedule_button.setFont(QFont('Arial', 10))
        self.schedule_button.setMinimumHeight(40)
        self.schedule_button.clicked.connect(self.show_schedule_config)
        button_layout.addWidget(self.schedule_button)

        main_layout.addLayout(button_layout)
        
        # Estilizando a interface
        self.apply_style()
        
    def apply_style(self):
        # Estilo geral
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                background-color: #2980b9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2980b9;
                width: 20px;
            }
        """)
        
        # Botão vermelho para o botão de parar
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        # Botão cinza para o botão de sair
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        
        # Botão azul claro para configuração de horários
        self.schedule_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
    def setupLogging(self):
        # Remover handlers existentes
        logging.getLogger().handlers = []
        
        # Configurar novo handler para a interface
        self.log_handler = QTextEditLogger()
        self.log_handler.log_signal.connect(self.update_log)
        
        # Configurar logging com nível DEBUG para capturar todos os logs
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[
                self.log_handler,
                logging.StreamHandler()  # Mantém os logs no terminal também
            ]
        )
        
        # Define o nível de log para módulos específicos
        logging.getLogger('selenium').setLevel(logging.INFO)
        logging.getLogger('urllib3').setLevel(logging.INFO)
        
        logging.info("Sistema de logging inicializado")
        
    @pyqtSlot(str, int)
    def update_log(self, message, level):
        # Mostrar todos os logs, não apenas warnings e errors
        color = QColor(0, 0, 0)  # Preto para INFO
        if level >= logging.ERROR:
            color = QColor(255, 0, 0)  # Vermelho para ERROR
        elif level >= logging.WARNING:
            color = QColor(255, 165, 0)  # Laranja para WARNING
        elif level >= logging.INFO:
            color = QColor(0, 70, 140)  # Azul para INFO

        self.log_area.setTextColor(color)
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
    
    def start_update(self):
        if self.running:
            return
            
        self.running = True
        self.stop_event.clear()
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Atualizando o sistema SSW...")
        
        # Log no arquivo e na interface
        logging.info("Iniciando processo de atualização do sistema SSW...")
        self.log_direto("INICIANDO ATUALIZAÇÃO DO SISTEMA")
        
        # Função para verificar conexão e executar o processamento em um thread separado
        def update_process():
            try:
                logging.info("Verificando conexão com a internet...")
                if not ssw_updater.verificar_conexao():
                    logging.error("Falha na conexão à internet. Verifique sua conexão e tente novamente.")
                    self.update_status("Falha na conexão", error=True)
                    return
                
                logging.info("Conexão internet OK! Iniciando atualização do sistema...")
                
                # Obter placas e localizações
                logging.info("Consultando placas e localizações dos veículos...")
                try:
                    _, veiculos_com_localizacao = ssw_updater.processador_placas.processar_localizacao_veiculos()
                    
                    if not veiculos_com_localizacao:
                        logging.warning("Nenhum veículo com localização encontrado. Encerrando processamento.")
                        self.update_status("Nenhum veículo encontrado", warning=True)
                        self.log_direto("ALERTA: Nenhum veículo com localização foi encontrado!")
                        return
                    
                    total_veiculos = len(veiculos_com_localizacao)
                    logging.info(f"Total de {total_veiculos} veículos com localização obtidos.")
                    self.log_direto(f"CONSULTA: {total_veiculos} veículos encontrados para atualização")
                    
                    # Iterar sobre cada veículo
                    self.update_progress_range(0, total_veiculos)
                    
                    for i, veiculo_info in enumerate(veiculos_com_localizacao):
                        if self.stop_event.is_set():
                            logging.info("Processo interrompido pelo usuário.")
                            break
                            
                        placa = veiculo_info.get('placa')
                        cidade = veiculo_info.get('cidade')
                        estado = veiculo_info.get('estado')
                        
                        if not all([placa, cidade, estado]):
                            logging.warning(f"Veículo {i+1} com dados incompletos. Pulando: {veiculo_info}")
                            continue
                        
                        self.update_status(f"Processando veículo {i+1}/{total_veiculos}: {placa}")
                        self.update_progress_value(i)
                        
                        logging.info(f"Atualizando veículo {i+1}/{total_veiculos}: "
                                    f"Placa {placa} - {cidade}/{estado}")
                        
                        try:
                            ssw_updater.atualizar_sistema_para_placa(placa, cidade, estado)
                            logging.info(f"Veículo {placa} atualizado com sucesso no sistema.")
                            # Log a cada 5 veículos ou em casos específicos
                            if (i+1) % 5 == 0 or i == 0 or i == total_veiculos-1:
                                self.log_direto(f"ATUALIZADO: Veículo {placa} ({cidade}/{estado})")
                        except Exception as e:
                            logging.error(f"Erro ao atualizar veículo {placa}: {e}")
                            self.log_direto(f"ERRO: Falha ao atualizar veículo {placa}")
                        
                        # Atualiza progresso
                        perc_concluido = int((i+1) / total_veiculos * 100)
                        if perc_concluido % 25 == 0 and i > 0:  # Log a cada 25% de progresso
                            logging.info(f"Progresso: {perc_concluido}% concluído ({i+1}/{total_veiculos})")
                            self.log_direto(f"PROGRESSO: {perc_concluido}% concluído ({i+1}/{total_veiculos} veículos)")
                        
                        if i < total_veiculos - 1 and not self.stop_event.is_set():
                            logging.info("Aguardando intervalo de 5 segundos antes do próximo veículo...")
                            time.sleep(5)
                    
                    if not self.stop_event.is_set():
                        logging.info("Atualização de todos os veículos concluída com sucesso!")
                        self.update_status("Processamento concluído", success=True)
                        self.log_direto("SUCESSO: Atualização de todos os veículos concluída!")
                    
                except Exception as e:
                    logging.error(f"Erro ao obter dados de veículos: {e}", exc_info=True)
                    self.update_status("Erro ao obter dados de veículos", error=True)
            
            except Exception as e:
                logging.error(f"Erro não tratado no processo: {e}", exc_info=True)
                self.update_status("Erro não tratado", error=True)
            
            finally:
                if not self.stop_event.is_set():
                    self.stop_event.set()
                self.running_completed()
                logging.info("Processo de atualização finalizado.")
        
        # Iniciar thread
        self.thread = threading.Thread(target=update_process)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_update(self):
        if not self.running:
            return
            
        self.stop_event.set()
        self.status_label.setText("Parando o processo...")
        logging.info("Solicitação para interromper o processo recebida. Finalizando operações...")
        self.log_direto("AVISO: Interrompendo o processo de atualização...")
        
        # Desabilitar botão de parar para evitar múltiplos cliques
        self.stop_button.setEnabled(False)
    
    def running_completed(self):
        self.running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.exit_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if self.stop_event.is_set():
            if self.status_label.text() != "Processamento concluído":
                self.status_label.setText("Processo interrompido")
                logging.info("Processo finalizado pelo usuário.")
                self.log_direto("AVISO: Processo de atualização interrompido pelo usuário")

        # Aguarda 3 segundos e limpa a área de log
        QTimer.singleShot(3000, self.clear_log_area)

    def clear_log_area(self):
        self.log_area.clear()
        self.log_area.append("Sistema pronto para nova execução.")
    
    def close_application(self):
        # Simplified close application method
        if self.running:
            self.stop_event.set()
            logging.info("Forçando encerramento do programa...")
        
        # Force close any remaining browser windows
        try:
            if hasattr(ssw_updater, 'driver'):
                ssw_updater.driver.quit()
                logging.info("Driver do navegador fechado.")
        except Exception as e:
            logging.warning(f"Não foi possível fechar o driver: {e}")
        
        logging.info("Aplicativo encerrado pelo usuário.")
        
        # Close the application immediately
        self.close()
        sys.exit(0)

    def closeEvent(self, event):
        # Simplified close event handler - always accept
        self.stop_event.set()
        logging.info("Janela do aplicativo fechada.")
        event.accept()
    
    # Métodos para atualizar a interface a partir de threads
    def update_status(self, message, error=False, warning=False, success=False):
        # Usar QTimer.singleShot para executar no thread da UI
        QTimer.singleShot(0, lambda: self._update_status_ui(message, error, warning, success))
    
    def _update_status_ui(self, message, error=False, warning=False, success=False):
        self.status_label.setText(message)
        
        # Aplicar estilo baseado no tipo de mensagem
        style = "QLabel { font-weight: bold; }"
        if error:
            style += "QLabel { color: #e74c3c; }"
        elif warning:
            style += "QLabel { color: #f39c12; }"
        elif success:
            style += "QLabel { color: #27ae60; }"
        else:
            style += "QLabel { color: #2980b9; }"
            
        self.status_label.setStyleSheet(style)
    
    def update_progress_range(self, minimum, maximum):
        QTimer.singleShot(0, lambda: self._update_progress_range_ui(minimum, maximum))
    
    def _update_progress_range_ui(self, minimum, maximum):
        self.progress_bar.setRange(minimum, maximum)
    
    def update_progress_value(self, value):
        QTimer.singleShot(0, lambda: self._update_progress_value_ui(value))
    
    def _update_progress_value_ui(self, value):
        self.progress_bar.setValue(value)

    def show_schedule_config(self):
        logging.info("Abrindo diálogo de configuração de horários...")
        dialog = ScheduleConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Update schedules immediately when dialog is accepted
            self.schedules = dialog.get_schedules()
            
            # Atualiza a interface
            if self.schedules:
                horarios_str = ', '.join(self.schedules)
                msg = f"Horários configurados: {horarios_str}"
                logging.info(msg)
                self.log_direto(f"CONFIGURAÇÃO: Novos horários configurados: {horarios_str}")
                self.update_status("Horários atualizados", success=True)
            else:
                logging.info("Nenhum horário configurado")
                self.log_direto("CONFIGURAÇÃO: Todos os horários foram removidos")
                self.update_status("Sem horários configurados", warning=True)
                
            # Restart the timer to ensure immediate check
            self.setup_schedule_timer()

    def setup_schedule_timer(self):
        # Cancel existing timer if it exists
        if hasattr(self, 'schedule_timer') and self.schedule_timer.isActive():
            self.schedule_timer.stop()
        
        # Create new timer
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_schedule)
        self.schedule_timer.start(60000)  # 60000 ms = 1 minuto
        logging.info("Timer de verificação de agendamentos iniciado")
        
        # Carrega horários existentes
        try:
            with open('schedules.json', 'r') as f:
                self.schedules = json.load(f)
                if self.schedules:
                    logging.info(f"Horários carregados: {', '.join(self.schedules)}")
                else:
                    logging.info("Nenhum horário de execução configurado")
        except FileNotFoundError:
            logging.info("Arquivo de horários não encontrado. Nenhum agendamento ativo.")
            self.schedules = []

    def check_schedule(self):
        current_time = datetime.now().strftime("%H:%M")
        
        # A cada 15 minutos, exibe mensagem de verificação
        current_minute = int(datetime.now().strftime("%M"))
        if current_minute % 15 == 0:
            logging.info(f"Verificando agendamentos - Hora atual: {current_time}")
            
            if hasattr(self, 'schedules') and self.schedules:
                horarios = ', '.join(self.schedules)
                logging.info(f"Próximos horários: {horarios}")
                
                # A cada hora exata, exibe os horários na interface
                if current_minute == 0:
                    self.log_direto(f"AGENDAMENTO: Próximos horários de execução: {horarios}")
        
        # Verifica se há um horário agendado para agora
        if hasattr(self, 'schedules') and current_time in self.schedules:
            if not self.running:
                msg = f"Iniciando atualização agendada para: {current_time}"
                logging.info(msg)
                self.log_direto(f"AGENDAMENTO: Iniciando atualização automática programada para {current_time}")
                self.update_status(msg, success=True)
                self.start_update()
            else:
                msg = "Horário agendado encontrado, mas uma atualização já está em andamento"
                logging.warning(msg)
                self.log_direto(f"ALERTA: Horário agendado {current_time} ignorado - atualização já em andamento")
                self.update_status(msg, warning=True)

class ScheduleConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configurar Horários')
        self.setMinimumWidth(300)
        self.setup_ui()
        self.load_schedules()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Lista de horários
        self.schedule_list = QListWidget()
        layout.addWidget(QLabel("Horários configurados:"))
        layout.addWidget(self.schedule_list)
        
        # Botões de adicionar/remover
        time_layout = QHBoxLayout()
        
        # Time picker
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        time_layout.addWidget(self.time_edit)
        
        # Botão adicionar
        add_button = QPushButton("Adicionar")
        add_button.clicked.connect(self.add_time)
        time_layout.addWidget(add_button)
        
        # Botão remover
        remove_button = QPushButton("Remover")
        remove_button.clicked.connect(self.remove_selected_time)
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        time_layout.addWidget(remove_button)
        
        layout.addLayout(time_layout)
        
        # Botões de OK/Cancelar
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def remove_selected_time(self):
        current_item = self.schedule_list.currentItem()
        if current_item:
            row = self.schedule_list.row(current_item)
            horario = current_item.text()
            self.schedule_list.takeItem(row)
            self.save_schedules()
            logging.info(f"Horário removido: {horario}")

    def add_time(self):
        time_text = self.time_edit.time().toString("HH:mm")
        # Verifica se o horário já existe
        existing_items = [self.schedule_list.item(i).text() 
                         for i in range(self.schedule_list.count())]
        if time_text not in existing_items:
            item = QListWidgetItem(time_text)
            self.schedule_list.addItem(item)
            self.save_schedules()
            logging.info(f"Novo horário adicionado: {time_text}")
        else:
            logging.warning(f"O horário {time_text} já está configurado")

    def load_schedules(self):
        try:
            with open('schedules.json', 'r') as f:
                schedules = json.load(f)
                for time_str in schedules:
                    self.schedule_list.addItem(QListWidgetItem(time_str))
            logging.info(f"Carregados {len(schedules)} horários configurados")
        except FileNotFoundError:
            logging.info("Nenhum arquivo de configuração de horários encontrado")

    def save_schedules(self):
        schedules = [self.schedule_list.item(i).text() 
                    for i in range(self.schedule_list.count())]
        with open('schedules.json', 'w') as f:
            json.dump(schedules, f)
        logging.info(f"Configurações de horários salvas: {len(schedules)} horários")

    def get_schedules(self):
        return [self.schedule_list.item(i).text() 
                for i in range(self.schedule_list.count())]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SSWUpdaterApp()
    window.show()
    sys.exit(app.exec_())