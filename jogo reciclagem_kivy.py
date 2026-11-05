# ============================================================
# JOGO RECICLAGEM - VERSAO KIVY
# Executa no computador pelo VS Code e pode ser empacotado
# para Android. Mantenha as imagens e os sons na mesma pasta.
#
# Instalar no computador:
#     python -m pip install kivy
#
# Executar:
#     python main.py
# ============================================================

import os
import random
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.uix.widget import Widget
from kivy.core.window import Window


# ------------------------------------------------------------
# CONFIGURACAO
# ------------------------------------------------------------

LARGURA, ALTURA = 1280, 720
FPS = 60
PASTA = os.path.dirname(os.path.abspath(__file__))

# No computador, abre em uma janela 16:9. No Android, o Kivy
# utiliza a tela disponivel.
try:
    Window.size = (LARGURA, ALTURA)
    Window.minimum_width = 900
    Window.minimum_height = 506
except Exception:
    pass

BRANCO = (1, 1, 1, 1)
PRETO = (25 / 255, 25 / 255, 25 / 255, 1)
VERDE = (35 / 255, 135 / 255, 65 / 255, 1)
VERMELHO = (190 / 255, 45 / 255, 45 / 255, 1)
AMARELO = (1, 225 / 255, 90 / 255, 1)

PONTOS_POR_ACERTO = 10
VELOCIDADE_CAMINHANTE = 2.5
TEMPO_MIN_RESIDUO = 0
TEMPO_MAX_RESIDUO = 600
TEMPO_REACAO_LIXEIRA = 0.9
GRAVIDADE = 0.55
VELOCIDADE_MAXIMA_QUEDA = 14
ALTURA_DO_CHAO = 555

CATEGORIAS = ["papel", "vidro", "metal", "plastico", "organico"]
NOMES = {
    "papel": "PAPEL",
    "vidro": "VIDRO",
    "metal": "METAL",
    "plastico": "PLÁSTICO",
    "organico": "ORGÂNICO",
}

LARGURA_RESIDUO = 80
ALTURA_RESIDUO = 80
LARGURA_CAMINHANTE = 105
ALTURA_CAMINHANTE = 155
LARGURA_LIXEIRA = 105
ALTURA_LIXEIRA = 145

POSICOES_LIXEIRAS = {
    "papel": (100, 390),
    "vidro": (320, 390),
    "metal": (540, 390),
    "plastico": (760, 390),
    "organico": (980, 390),
}

ELOGIOS = [
    "Fantastico!", "Excelente!", "Otimo trabalho!", "Muito bem!",
    "Mandou bem!", "Parabens!", "Isso ai!", "Acertou em cheio!",
    "Perfeito!", "Voce conseguiu!"
]
BRONCAS = [
    "Nao recebo esse lixo!", "Esta errado!", "Tente de novo!",
    "Aqui nao!", "Preste atencao!", "Esse nao e o lugar!",
    "Vamos tentar novamente!", "Separe corretamente!",
    "Nao e aqui!", "Cuidado com a separacao!"
]


# ------------------------------------------------------------
# CARREGAMENTO DE ARQUIVOS
# ------------------------------------------------------------

def caminho_existente(nomes):
    for nome in nomes:
        caminho = os.path.join(PASTA, nome)
        if os.path.isfile(caminho):
            return caminho
    return None


def carregar_textura(nomes):
    caminho = caminho_existente(nomes)
    if not caminho:
        return None
    try:
        return CoreImage(caminho).texture
    except Exception as erro:
        print(f"Erro ao carregar imagem {caminho}: {erro}")
        return None


def carregar_som(nome, volume=1.0):
    caminho = os.path.join(PASTA, nome)
    if not os.path.isfile(caminho):
        print(f"Som nao encontrado: {nome}")
        return None
    try:
        som = SoundLoader.load(caminho)
        if som:
            som.volume = volume
        else:
            print(f"Formato de audio nao suportado: {nome}")
        return som
    except Exception as erro:
        print(f"Erro ao carregar som {nome}: {erro}")
        return None


FUNDO_MENU = carregar_textura(["recicle.png"])
FUNDO_JOGO = carregar_textura(["bacground.png"])

CAMINHANTE = []
for i in range(1, 4):
    textura = carregar_textura([f"walck{i}.png"])
    if textura:
        CAMINHANTE.append(textura)

SPRITES_RESIDUOS = {categoria: [] for categoria in CATEGORIAS}
for categoria in CATEGORIAS:
    for numero in range(1, 6):
        textura = carregar_textura([f"{categoria}{numero}.png"])
        if textura:
            SPRITES_RESIDUOS[categoria].append(textura)
        else:
            print(f"AVISO: imagem nao encontrada: {categoria}{numero}.png")


def nomes_idle(categoria, numero):
    return [
        f"{categoria} idel{numero}.png",
        f"{categoria} idel {numero}.png",
        f"{categoria} idle{numero}.png",
        f"{categoria} idle {numero}.png",
        f"{categoria} ideal{numero}.png",
    ]


SPRITES_LIXEIRAS = {}
for categoria in CATEGORIAS:
    SPRITES_LIXEIRAS[categoria] = {
        "idle": [
            carregar_textura(nomes_idle(categoria, 1)),
            carregar_textura(nomes_idle(categoria, 2)),
        ],
        "certo": carregar_textura(
            [f"{categoria} certo.png", f"{categoria} correta.png"]
        ),
        "errado": carregar_textura(
            [f"{categoria} errado.png", f"{categoria} incorreto.png"]
        ),
    }

MUSICA = carregar_som("son de fundo.mp3", 0.5)
SOM_PASSO = carregar_som("passo.mp3", 0.25)


# ------------------------------------------------------------
# FUNCOES DE APOIO VISUAL
# ------------------------------------------------------------

def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


class JogoReciclagem(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.estado = "inicio"
        self.pontuacao = 0
        self.residuos_criados = 0
        self.residuos_corretos = 0
        self.residuos_chao = []
        self.residuo_selecionado = None

        self.mensagem_feedback = ""
        self.cor_feedback = PRETO
        self.tempo_feedback = 0

        self.tempo_reacao = {c: 0 for c in CATEGORIAS}
        self.resultado_lixeiras = {c: None for c in CATEGORIAS}
        self.mensagens_lixeiras = {c: "" for c in CATEGORIAS}

        self.fila_categorias = []
        self.ultima_categoria = None

        self.caminhante_x = 640
        self.caminhante_y = 400
        self.direcao = 1
        self.indice_animacao = 0
        self.contador_animacao = 0
        self.proximo_residuo = None

        self.animacao_lixeiras = {
            c: {"frame": 0, "proxima_troca": self.agora_ms() + random.randint(1800, 4000)}
            for c in CATEGORIAS
        }

        self.lixeiras = {
            c: (POSICOES_LIXEIRAS[c][0], POSICOES_LIXEIRAS[c][1],
                LARGURA_LIXEIRA, ALTURA_LIXEIRA)
            for c in CATEGORIAS
        }

        self.botao_iniciar = (LARGURA // 2 - 145, 510, 290, 72)
        self.botao_comecar = (LARGURA // 2 - 145, 585, 290, 72)
        self.botao_menu = (LARGURA // 2 - 145, 535, 290, 72)

        self.musica_tocando = False
        self._touch_id = None

        Window.bind(on_keyboard=self.tecla_teclado)
        Clock.schedule_interval(self.atualizar, 1 / FPS)

    @staticmethod
    def agora_ms():
        return time.monotonic() * 1000

    # Converte as coordenadas do Kivy (origem inferior esquerda)
    # para o sistema usado no projeto original (origem superior esquerda).
    def escala_tela(self):
        if self.width <= 0 or self.height <= 0:
            return 1, 1, 0, 0
        escala = min(self.width / LARGURA, self.height / ALTURA)
        largura_real = LARGURA * escala
        altura_real = ALTURA * escala
        offset_x = (self.width - largura_real) / 2
        offset_y = (self.height - altura_real) / 2
        return escala, escala, offset_x, offset_y

    def toque_para_jogo(self, touch):
        sx, sy, ox, oy = self.escala_tela()
        x = (touch.x - ox) / sx
        y = (self.height - touch.y - oy) / sy
        return x, y

    def ponto_tela(self, x, y, largura=0, altura=0):
        sx, sy, ox, oy = self.escala_tela()
        return (
            ox + x * sx,
            self.height - oy - (y + altura) * sy
        )

    def tamanho_tela(self, largura, altura):
        sx, sy, _, _ = self.escala_tela()
        return largura * sx, altura * sy

    @staticmethod
    def dentro(pos, ret):
        x, y = pos
        rx, ry, rw, rh = ret
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    @staticmethod
    def colisao(a, b):
        return (
            a["x"] < b[0] + b[2] and
            a["x"] + a["w"] > b[0] and
            a["y"] < b[1] + b[3] and
            a["y"] + a["h"] > b[1]
        )

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def limpar_tela(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.12, 0.16, 0.12, 1)
            Rectangle(pos=self.pos, size=self.size)

    def desenhar_imagem(self, textura, x, y, w, h, flip_x=False):
        if not textura:
            return
        pos = self.ponto_tela(x, y, w, h)
        size = self.tamanho_tela(w, h)
        with self.canvas:
            Color(1, 1, 1, 1)
            if flip_x:
                Rectangle(
                    texture=textura, pos=pos, size=size,
                    tex_coords=(1, 0, 0, 0, 0, 1, 1, 1)
                )
            else:
                Rectangle(texture=textura, pos=pos, size=size)

    def desenhar_retangulo(self, x, y, w, h, cor, raio=0,
                           borda=None, largura_borda=1):
        pos = self.ponto_tela(x, y, w, h)
        size = self.tamanho_tela(w, h)
        with self.canvas:
            Color(*cor)
            if raio:
                RoundedRectangle(pos=pos, size=size, radius=[raio * self.escala_tela()[0]])
            else:
                Rectangle(pos=pos, size=size)
            if borda:
                Color(*borda)
                Line(rounded_rectangle=(pos[0], pos[1], size[0], size[1],
                                        raio * self.escala_tela()[0]),
                     width=largura_borda * self.escala_tela()[0])

    def desenhar_elipse(self, x, y, w, h, cor):
        pos = self.ponto_tela(x, y, w, h)
        size = self.tamanho_tela(w, h)
        with self.canvas:
            Color(*cor)
            Ellipse(pos=pos, size=size)

    def desenhar_texto(self, mensagem, x, y, tamanho=25, cor=PRETO,
                       bold=False, centro=True, largura_max=None):
        if not mensagem:
            return
        sx, _, _, _ = self.escala_tela()
        label = CoreLabel(
            text=str(mensagem),
            font_size=max(8, tamanho * sx),
            bold=bold,
            color=cor,
            halign="center",
            valign="middle"
        )
        if largura_max:
            label.text_size = (largura_max * sx, None)
        label.refresh()
        textura = label.texture
        w, h = textura.size
        if centro:
            px, py = self.ponto_tela(x - w / sx / 2, y - h / sx / 2,
                                     w / sx, h / sx)
        else:
            px, py = self.ponto_tela(x, y, w / sx, h / sx)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=textura, pos=(px, py), size=(w, h))

    def desenhar_fundo(self, textura, cor=(175 / 255, 220 / 255, 180 / 255, 1)):
        if textura:
            self.desenhar_imagem(textura, 0, 0, LARGURA, ALTURA)
        else:
            self.desenhar_retangulo(0, 0, LARGURA, ALTURA, cor)

    def desenhar_botao(self, mensagem, ret, cor=VERDE):
        x, y, w, h = ret
        self.desenhar_retangulo(x, y, w, h, cor, 16, BRANCO, 3)
        self.desenhar_texto(mensagem, x + w / 2, y + h / 2,
                            34, BRANCO, True)

    def desenhar_sombra(self, x, y, w, h):
        self.desenhar_elipse(x, y, w, h, (0.08, 0.08, 0.08, 0.18))
        self.desenhar_elipse(x + w * 0.08, y + h * 0.12,
                             w * 0.84, h * 0.76, (0.08, 0.08, 0.08, 0.13))

    # --------------------------------------------------------
    # LOGICA DO JOGO
    # --------------------------------------------------------

    def iniciar_musica(self):
        if MUSICA and not self.musica_tocando:
            try:
                MUSICA.loop = True
                MUSICA.play()
                self.musica_tocando = True
            except Exception as erro:
                print("Nao foi possivel iniciar a musica:", erro)

    def parar_musica(self):
        if MUSICA and self.musica_tocando:
            try:
                MUSICA.stop()
            except Exception:
                pass
        self.musica_tocando = False

    def tocar_passo(self):
        if SOM_PASSO:
            try:
                SOM_PASSO.stop()
                SOM_PASSO.play()
            except Exception:
                pass

    def sortear_categoria(self):
        if not self.fila_categorias:
            self.fila_categorias = CATEGORIAS.copy()
            random.shuffle(self.fila_categorias)
            if (self.ultima_categoria is not None and
                    self.fila_categorias[0] == self.ultima_categoria):
                indice = random.randint(1, len(self.fila_categorias) - 1)
                self.fila_categorias[0], self.fila_categorias[indice] = (
                    self.fila_categorias[indice], self.fila_categorias[0]
                )
        categoria = self.fila_categorias.pop(0)
        self.ultima_categoria = categoria
        return categoria

    def criar_residuo(self, x=None):
        categoria = self.sortear_categoria()
        if x is None:
            x = self.caminhante_x + 52
        imagens = SPRITES_RESIDUOS[categoria]
        textura = random.choice(imagens) if imagens else None

        w, h = LARGURA_RESIDUO, ALTURA_RESIDUO
        if textura:
            proporcao = min(w / textura.width, h / textura.height)
            w = max(1, textura.width * proporcao)
            h = max(1, textura.height * proporcao)

        self.residuos_chao.append({
            "categoria": categoria,
            "textura": textura,
            "x": limitar(x - w / 2, 0, LARGURA - w),
            "y": ALTURA_DO_CHAO - h,
            "w": w,
            "h": h,
            "id": self.residuos_criados,
            "caindo": False,
            "velocidade_y": 0,
        })
        self.residuos_criados += 1

    def reiniciar_partida(self):
        self.pontuacao = 0
        self.residuos_criados = 0
        self.residuos_corretos = 0
        self.residuos_chao = []
        self.residuo_selecionado = None
        self.mensagem_feedback = ""
        self.cor_feedback = PRETO
        self.tempo_feedback = 0
        self.caminhante_x = 100
        self.direcao = 1
        self.indice_animacao = 0
        self.contador_animacao = 0
        agora = self.agora_ms()
        self.proximo_residuo = agora + random.randint(
            TEMPO_MIN_RESIDUO, TEMPO_MAX_RESIDUO
        )
        self.tempo_reacao = {c: 0 for c in CATEGORIAS}
        self.resultado_lixeiras = {c: None for c in CATEGORIAS}
        self.mensagens_lixeiras = {c: "" for c in CATEGORIAS}
        self.fila_categorias = []
        self.ultima_categoria = None
        for categoria in CATEGORIAS:
            self.animacao_lixeiras[categoria]["frame"] = 0
            self.animacao_lixeiras[categoria]["proxima_troca"] = (
                agora + random.randint(1800, 4000)
            )

    def atualizar_animacao_lixeiras(self, agora):
        for categoria in CATEGORIAS:
            animacao = self.animacao_lixeiras[categoria]
            if agora >= animacao["proxima_troca"]:
                sprites = SPRITES_LIXEIRAS[categoria]["idle"]
                if animacao["frame"] == 0:
                    if sprites[1] is not None:
                        animacao["frame"] = 1
                        animacao["proxima_troca"] = agora + random.randint(120, 220)
                    else:
                        animacao["proxima_troca"] = agora + random.randint(1800, 4000)
                else:
                    animacao["frame"] = 0
                    animacao["proxima_troca"] = agora + random.randint(1800, 4000)

    def atualizar_residuos_caindo(self, agora):
        for item in self.residuos_chao[:]:
            if item is self.residuo_selecionado or not item["caindo"]:
                continue

            item["velocidade_y"] = min(
                item["velocidade_y"] + GRAVIDADE,
                VELOCIDADE_MAXIMA_QUEDA
            )
            item["y"] += int(item["velocidade_y"])

            categoria_residuo = item["categoria"]
            if self.colisao(item, self.lixeiras[categoria_residuo]):
                self.residuos_chao.remove(item)
                self.pontuacao += PONTOS_POR_ACERTO
                self.residuos_corretos += 1
                self.mensagem_feedback = "Resposta correta! +10 pontos."
                self.cor_feedback = VERDE
                self.tempo_feedback = agora + 2200
                self.resultado_lixeiras[categoria_residuo] = "certo"
                self.mensagens_lixeiras[categoria_residuo] = random.choice(ELOGIOS)
                self.tempo_reacao[categoria_residuo] = (
                    agora + TEMPO_REACAO_LIXEIRA * 1000
                )
                continue

            for categoria_lixeira in CATEGORIAS:
                if categoria_lixeira == categoria_residuo:
                    continue
                if self.colisao(item, self.lixeiras[categoria_lixeira]):
                    if (self.resultado_lixeiras[categoria_lixeira] != "errado" or
                            agora >= self.tempo_reacao[categoria_lixeira]):
                        self.resultado_lixeiras[categoria_lixeira] = "errado"
                        self.mensagens_lixeiras[categoria_lixeira] = random.choice(BRONCAS)
                        self.tempo_reacao[categoria_lixeira] = (
                            agora + TEMPO_REACAO_LIXEIRA * 1000
                        )
                    break

            if item["y"] + item["h"] >= ALTURA_DO_CHAO:
                item["y"] = ALTURA_DO_CHAO - item["h"]
                item["caindo"] = False
                item["velocidade_y"] = 0

    def atualizar_jogo(self, agora):
        self.caminhante_x += VELOCIDADE_CAMINHANTE * self.direcao

        if self.caminhante_x >= LARGURA - 130:
            self.caminhante_x = LARGURA - 130
            self.direcao = -1
            self.proximo_residuo = agora + random.randint(
                TEMPO_MIN_RESIDUO, TEMPO_MAX_RESIDUO
            )
        elif self.caminhante_x <= 25:
            self.caminhante_x = 25
            self.direcao = 1
            self.proximo_residuo = agora + random.randint(
                TEMPO_MIN_RESIDUO, TEMPO_MAX_RESIDUO
            )

        if self.proximo_residuo is not None and agora >= self.proximo_residuo:
            self.criar_residuo(self.caminhante_x + 52)
            self.proximo_residuo = None

        self.contador_animacao += 1
        if self.contador_animacao >= 7:
            self.contador_animacao = 0
            if CAMINHANTE:
                self.indice_animacao = (self.indice_animacao + 1) % len(CAMINHANTE)
                if self.indice_animacao == 1:
                    self.tocar_passo()

        self.atualizar_residuos_caindo(agora)

        for categoria in CATEGORIAS:
            if agora >= self.tempo_reacao[categoria]:
                self.resultado_lixeiras[categoria] = None
                self.mensagens_lixeiras[categoria] = ""

        if self.tempo_feedback and agora > self.tempo_feedback:
            self.mensagem_feedback = ""
            self.tempo_feedback = 0

    # --------------------------------------------------------
    # ARRASTAR E SOLTAR
    # --------------------------------------------------------

    def tentar_classificar(self, posicao):
        if self.residuo_selecionado is not None:
            return
        x, y = posicao
        for item in reversed(self.residuos_chao):
            if (not item["caindo"] and
                    item["x"] <= x <= item["x"] + item["w"] and
                    item["y"] <= y <= item["y"] + item["h"]):
                self.residuo_selecionado = item
                item["offset_x"] = item["x"] - x
                item["offset_y"] = item["y"] - y
                self.mensagem_feedback = ""
                self.tempo_feedback = 0
                return

    def arrastar_residuo(self, posicao):
        if self.residuo_selecionado is None:
            return
        item = self.residuo_selecionado
        item["x"] = posicao[0] + item["offset_x"]
        item["y"] = posicao[1] + item["offset_y"]

    def soltar_residuo(self):
        if self.residuo_selecionado is None:
            return
        self.residuo_selecionado["caindo"] = True
        self.residuo_selecionado["velocidade_y"] = 0
        self.residuo_selecionado = None

    # --------------------------------------------------------
    # TELAS
    # --------------------------------------------------------

    def desenhar_inicio(self):
        self.desenhar_fundo(FUNDO_MENU)
        self.desenhar_botao("INICIAR JOGO", self.botao_iniciar)

    def desenhar_tutorial(self):
        self.desenhar_fundo(FUNDO_MENU)
        self.desenhar_retangulo(
            215, 105, 850, 430, (1, 1, 1, 0.86), 24
        )
        self.desenhar_texto("COMO JOGAR", LARGURA / 2, 160, 54, VERDE, True)

        textura = SPRITES_LIXEIRAS["papel"]["idle"][0]
        if textura:
            self.desenhar_imagem(textura, LARGURA / 2 - 65, 205, 105, 145)
        else:
            self.desenhar_retangulo(
                LARGURA / 2 - 55, 220, 110, 135, VERDE, 15
            )
            self.desenhar_texto("PAPEL", LARGURA / 2, 280, 25, BRANCO, True)

        self.desenhar_texto(
            "1. Observe os residuos que o caminhante deixa na praca.",
            LARGURA / 2, 390, 25, PRETO, True
        )
        self.desenhar_texto(
            "2. Toque e arraste um residuo do chao.",
            LARGURA / 2, 430, 25, PRETO, True
        )
        self.desenhar_texto(
            "3. Solte-o sobre a lixeira correspondente.",
            LARGURA / 2, 470, 25, PRETO, True
        )
        self.desenhar_texto(
            "A cada acerto, voce ganha pontos!",
            LARGURA / 2, 515, 25, VERDE, True
        )
        self.desenhar_botao("COMEÇAR", self.botao_comecar)

    def desenhar_lixeira(self, categoria, agora):
        x, y, w, h = self.lixeiras[categoria]
        sprites = SPRITES_LIXEIRAS[categoria]
        reacao = self.resultado_lixeiras[categoria]

        if agora < self.tempo_reacao[categoria] and reacao == "certo" and sprites["certo"]:
            textura = sprites["certo"]
        elif agora < self.tempo_reacao[categoria] and reacao == "errado" and sprites["errado"]:
            textura = sprites["errado"]
        else:
            frame = self.animacao_lixeiras[categoria]["frame"]
            idle = sprites["idle"]
            textura = idle[frame] if frame < len(idle) and idle[frame] else idle[0]

        if textura:
            self.desenhar_imagem(textura, x, y, w, h)
        else:
            self.desenhar_retangulo(x, y, w, h, (80 / 255, 150 / 255, 90 / 255, 1), 12, PRETO, 2)
            self.desenhar_texto(NOMES[categoria], x + w / 2, y + h / 2, 19, BRANCO, True)

    def desenhar_balao(self, categoria, mensagem, tipo):
        x, y, w, h = self.lixeiras[categoria]
        largura, altura = 150, 62
        if tipo == "certo":
            bx = x + w + 8
            cor_borda = VERDE
        else:
            bx = x - largura - 8
            cor_borda = VERMELHO
        bx = limitar(bx, 5, LARGURA - largura - 5)
        by = limitar(y + 35, 5, ALTURA - altura - 5)

        self.desenhar_retangulo(bx, by, largura, altura, BRANCO, 13, cor_borda, 3)
        self.desenhar_texto(mensagem, bx + largura / 2, by + altura / 2,
                            19, PRETO, True, largura_max=largura - 14)

    def desenhar_jogo(self, agora):
        self.desenhar_fundo(FUNDO_JOGO, (180 / 255, 215 / 255, 175 / 255, 1))

        # Sombras das lixeiras e do caminhante.
        for categoria in CATEGORIAS:
            x, y, w, h = self.lixeiras[categoria]
            self.desenhar_sombra(x + 2, y + h - 4, 100, 22)

        self.desenhar_sombra(self.caminhante_x + 2, self.caminhante_y + 140, 100, 25)

        for item in self.residuos_chao:
            if not item["caindo"] and item is not self.residuo_selecionado:
                self.desenhar_sombra(item["x"] + 12, item["y"] + item["h"] - 1, 55, 13)

        # Nomes das lixeiras.
        for categoria in CATEGORIAS:
            x, y, w, h = self.lixeiras[categoria]
            self.desenhar_retangulo(x - 5, y - 32, w + 10, 28, BRANCO, 7, PRETO, 1)
            self.desenhar_texto(NOMES[categoria], x + w / 2, y - 18,
                                19, PRETO, True)

        # Pontuacao.
        self.desenhar_retangulo(
            LARGURA - 245, 25, 215, 65,
            (1, 1, 1, 0.88), 12, VERDE, 2
        )
        self.desenhar_texto(
            f"PONTOS: {self.pontuacao}",
            LARGURA - 137.5, 57.5, 25, PRETO, True
        )

        for categoria in CATEGORIAS:
            self.desenhar_lixeira(categoria, agora)

        # Residuos.
        for item in self.residuos_chao:
            if item["textura"]:
                self.desenhar_imagem(
                    item["textura"], item["x"], item["y"],
                    item["w"], item["h"]
                )
            else:
                self.desenhar_retangulo(
                    item["x"], item["y"], item["w"], item["h"],
                    BRANCO, 9, PRETO, 2
                )
                self.desenhar_texto(
                    NOMES[item["categoria"]],
                    item["x"] + item["w"] / 2,
                    item["y"] + item["h"] / 2,
                    16, PRETO, True
                )
            if item is self.residuo_selecionado:
                self.desenhar_retangulo(
                    item["x"] - 5, item["y"] - 5,
                    item["w"] + 10, item["h"] + 10,
                    (0, 0, 0, 0), 11, AMARELO, 4
                )

        # Caminhante.
        if CAMINHANTE:
            textura = CAMINHANTE[self.indice_animacao % len(CAMINHANTE)]
            self.desenhar_imagem(
                textura, self.caminhante_x, self.caminhante_y,
                LARGURA_CAMINHANTE, ALTURA_CAMINHANTE,
                self.direcao < 0
            )
        else:
            self.desenhar_elipse(
                self.caminhante_x + 28, self.caminhante_y + 5,
                44, 44, (70 / 255, 80 / 255, 150 / 255, 1)
            )
            self.desenhar_retangulo(
                self.caminhante_x + 32, self.caminhante_y + 48,
                36, 75, (70 / 255, 80 / 255, 150 / 255, 1), 10
            )

        # Baloes de reacao.
        for categoria in CATEGORIAS:
            reacao = self.resultado_lixeiras[categoria]
            if (agora < self.tempo_reacao[categoria] and
                    reacao in ("certo", "errado") and
                    self.mensagens_lixeiras[categoria]):
                self.desenhar_balao(
                    categoria, self.mensagens_lixeiras[categoria], reacao
                )

        # Feedback geral.
        if self.mensagem_feedback:
            self.desenhar_retangulo(
                180, 165, LARGURA - 360, 42, BRANCO, 10,
                self.cor_feedback, 2
            )
            self.desenhar_texto(
                self.mensagem_feedback, LARGURA / 2, 186,
                19, self.cor_feedback, True
            )

    def desenhar_resultado(self):
        self.desenhar_fundo(FUNDO_MENU)
        self.desenhar_retangulo(
            LARGURA / 2 - 325, 150, 650, 360,
            (1, 1, 1, 0.86), 25
        )
        self.desenhar_texto(
            "RESULTADO", LARGURA / 2, 225, 54, VERDE, True
        )
        self.desenhar_texto(
            f"SUA PONTUACAO: {self.pontuacao}",
            LARGURA / 2, 325, 34, PRETO, True
        )
        self.desenhar_texto(
            f"Residuos classificados corretamente: {self.residuos_corretos}",
            LARGURA / 2, 390, 25, PRETO, True
        )
        self.desenhar_texto(
            "Parabens por ajudar a manter a praca limpa!",
            LARGURA / 2, 445, 19, VERDE, True
        )
        self.desenhar_botao("VOLTAR AO MENU", self.botao_menu)

    # --------------------------------------------------------
    # ATUALIZACAO E EVENTOS
    # --------------------------------------------------------

    def atualizar(self, dt):
        agora = self.agora_ms()
        self.atualizar_animacao_lixeiras(agora)

        if self.estado == "jogo":
            self.atualizar_jogo(agora)

        self.limpar_tela()

        # Mantem o desenho proporcional em telas diferentes.
        sx, sy, ox, oy = self.escala_tela()
        with self.canvas:
            # Fundo das faixas laterais em telas que nao sejam 16:9.
            Color(0.08, 0.10, 0.08, 1)
            Rectangle(pos=self.pos, size=self.size)

        if self.estado == "inicio":
            self.desenhar_inicio()
        elif self.estado == "tutorial":
            self.desenhar_tutorial()
        elif self.estado == "jogo":
            self.desenhar_jogo(agora)
        elif self.estado == "pontuacao":
            self.desenhar_resultado()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        pos = self.toque_para_jogo(touch)

        if self.estado == "inicio":
            if self.dentro(pos, self.botao_iniciar):
                self.estado = "tutorial"
                return True

        elif self.estado == "tutorial":
            if self.dentro(pos, self.botao_comecar):
                self.reiniciar_partida()
                self.estado = "jogo"
                self.iniciar_musica()
                return True

        elif self.estado == "jogo":
            self.tentar_classificar(pos)
            if self.residuo_selecionado is not None:
                self._touch_id = touch.uid
                self.arrastar_residuo(pos)
                return True

        elif self.estado == "pontuacao":
            if self.dentro(pos, self.botao_menu):
                self.estado = "inicio"
                return True

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.estado == "jogo" and self.residuo_selecionado is not None:
            if self._touch_id == touch.uid:
                self.arrastar_residuo(self.toque_para_jogo(touch))
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.estado == "jogo" and self.residuo_selecionado is not None:
            if self._touch_id == touch.uid:
                self.arrastar_residuo(self.toque_para_jogo(touch))
                self.soltar_residuo()
                self._touch_id = None
                return True
        return super().on_touch_up(touch)

    def tecla_teclado(self, window, key, scancode, codepoint, modifiers):
        # ESC no computador retorna ao menu. No Android, o botao
        # voltar tambem pode acionar este evento, conforme o dispositivo.
        if key == 27:
            if self.estado == "inicio":
                self.parar_musica()
                App.get_running_app().stop()
            else:
                if self.estado == "jogo":
                    self.parar_musica()
                self.estado = "inicio"
                self.residuo_selecionado = None
            return True
        return False


class ReciclagemApp(App):
    def build(self):
        self.title = "Jogo Reciclagem"
        return JogoReciclagem()

    def on_stop(self):
        if self.root:
            self.root.parar_musica()


if __name__ == "__main__":
    ReciclagemApp().run()
