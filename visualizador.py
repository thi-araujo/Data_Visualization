"""Visualizador de Dados: abra uma planilha e monte gráficos sem escrever código.

    python visualizador.py

Requer pandas, matplotlib e openpyxl (pip install -r requirements.txt).
"""

from __future__ import annotations

import platform
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

import dados as dd  # noqa: E402
import funcoes as fn  # noqa: E402
import graficos as gr  # noqa: E402

CORES = {
    "fundo": "#0f172a",
    "painel": "#1e293b",
    "borda": "#334155",
    "texto": "#e2e8f0",
    "texto_suave": "#94a3b8",
    "destaque": "#38bdf8",
    "verde": "#22c55e",
    "vermelho": "#ef4444",
    "ambar": "#f59e0b",
}
NENHUMA = "(nenhuma)"
CONTAGEM = "(contagem)"
MAX_LINHAS_TABELA = 500

WINDOWS = platform.system() == "Windows"
FONTE = "Segoe UI" if WINDOWS else "Helvetica"


def configurar_estilo(raiz: tk.Tk) -> None:
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    sem_borda = dict(bordercolor=CORES["painel"], lightcolor=CORES["painel"], darkcolor=CORES["painel"])
    fundo_sem_borda = dict(bordercolor=CORES["fundo"], lightcolor=CORES["fundo"], darkcolor=CORES["fundo"])
    estilo.configure(".", background=CORES["fundo"], foreground=CORES["texto"], font=(FONTE, 10))
    estilo.configure("Painel.TFrame", background=CORES["painel"])
    estilo.configure("Painel.TLabel", background=CORES["painel"])
    estilo.configure("PainelSuave.TLabel", background=CORES["painel"], foreground=CORES["texto_suave"])
    estilo.configure("Titulo.TLabel", background=CORES["painel"], foreground=CORES["destaque"],
                     font=(FONTE, 11, "bold"))
    estilo.configure("Suave.TLabel", foreground=CORES["texto_suave"])
    estilo.configure("TNotebook", background=CORES["fundo"], borderwidth=0, tabmargins=(0, 0, 0, 0),
                     **fundo_sem_borda)
    estilo.configure("TNotebook.Tab", background=CORES["painel"], foreground=CORES["texto_suave"],
                     padding=(16, 7), borderwidth=0, font=(FONTE, 10, "bold"), **fundo_sem_borda)
    estilo.map("TNotebook.Tab", background=[("selected", CORES["borda"])],
               foreground=[("selected", CORES["destaque"])], expand=[("selected", (0, 0, 0, 0))])
    estilo.configure("TButton", background=CORES["borda"], foreground=CORES["texto"], borderwidth=0,
                     padding=(12, 6), font=(FONTE, 10, "bold"))
    estilo.map("TButton", background=[("disabled", CORES["painel"]), ("active", "#475569")],
               foreground=[("disabled", CORES["texto_suave"])])
    estilo.configure("Destaque.TButton", background=CORES["destaque"], foreground=CORES["fundo"])
    estilo.map("Destaque.TButton", background=[("disabled", CORES["painel"]), ("active", "#0ea5e9")])
    campo = dict(fieldbackground=CORES["fundo"], foreground=CORES["texto"], insertcolor=CORES["texto"],
                 bordercolor=CORES["borda"], lightcolor=CORES["fundo"], darkcolor=CORES["fundo"])
    estilo.configure("TEntry", **campo)
    estilo.configure("TCombobox", arrowcolor=CORES["texto"], background=CORES["borda"], **campo)
    estilo.map("TCombobox", fieldbackground=[("readonly", CORES["fundo"]), ("disabled", CORES["painel"])],
               foreground=[("readonly", CORES["texto"]), ("disabled", CORES["texto_suave"])],
               selectbackground=[("readonly", CORES["fundo"])], selectforeground=[("readonly", CORES["texto"])])
    raiz.option_add("*TCombobox*Listbox.background", CORES["painel"])
    raiz.option_add("*TCombobox*Listbox.foreground", CORES["texto"])
    raiz.option_add("*TCombobox*Listbox.selectBackground", CORES["borda"])
    estilo.configure("Treeview", background=CORES["painel"], fieldbackground=CORES["painel"],
                     foreground=CORES["texto"], borderwidth=0, rowheight=24, **sem_borda)
    estilo.configure("Treeview.Heading", background=CORES["borda"], foreground=CORES["texto_suave"],
                     borderwidth=0, font=(FONTE, 9, "bold"))
    estilo.map("Treeview.Heading", background=[("active", CORES["borda"])])
    estilo.map("Treeview", background=[("selected", CORES["borda"])])
    for orientacao in ("Vertical", "Horizontal"):
        estilo.configure(f"{orientacao}.TScrollbar", background=CORES["borda"], troughcolor=CORES["painel"],
                         borderwidth=0, arrowcolor=CORES["texto_suave"], **sem_borda)
        estilo.map(f"{orientacao}.TScrollbar", background=[("disabled", CORES["painel"])])


class Aplicativo(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Visualizador de Dados")
        self.geometry("1180x720")
        self.minsize(1040, 640)
        self.configure(bg=CORES["fundo"])
        configurar_estilo(self)

        self.df: pd.DataFrame | None = None
        self.colunas = dd.Colunas([], [])
        self.var_tipo = tk.StringVar(value="Dispersão")
        self.var_x = tk.StringVar()
        self.var_y = tk.StringVar()
        self.var_cor = tk.StringVar(value=NENHUMA)
        self.var_titulo = tk.StringVar()

        self._montar()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    # ------------------------------------------------------------------ tela

    def _montar(self) -> None:
        lateral = ttk.Frame(self, style="Painel.TFrame", padding=16, width=290)
        lateral.pack(side="left", fill="y", padx=(16, 0), pady=16)
        lateral.pack_propagate(False)

        ttk.Label(lateral, text="Dados", style="Titulo.TLabel").pack(anchor="w")
        ttk.Button(lateral, text="Abrir planilha...", style="Destaque.TButton", command=self.abrir).pack(
            fill="x", pady=(8, 4))
        ttk.Button(lateral, text="Usar exemplo (dados fictícios)", command=self.usar_exemplo).pack(fill="x")
        self.lbl_arquivo = ttk.Label(lateral, text="Nenhum arquivo aberto", style="PainelSuave.TLabel",
                                     wraplength=250, justify="left")
        self.lbl_arquivo.pack(anchor="w", pady=(8, 18))

        ttk.Label(lateral, text="Gráfico", style="Titulo.TLabel").pack(anchor="w")
        self.cmb_tipo = self._campo(lateral, "Tipo", self.var_tipo, list(gr.TIPOS))
        self.lbl_dica = ttk.Label(lateral, text="", style="PainelSuave.TLabel", wraplength=250, justify="left",
                                  font=(FONTE, 9))
        self.lbl_dica.pack(anchor="w", pady=(2, 4))
        self.cmb_x = self._campo(lateral, "Eixo X / grupos", self.var_x, [])
        self.cmb_y = self._campo(lateral, "Eixo Y / valor", self.var_y, [])
        self.cmb_cor = self._campo(lateral, "Cor por", self.var_cor, [])
        ttk.Label(lateral, text="Título (opcional)", style="PainelSuave.TLabel").pack(anchor="w", pady=(8, 2))
        titulo = ttk.Entry(lateral, textvariable=self.var_titulo)
        titulo.pack(fill="x", ipady=2)
        titulo.bind("<Return>", lambda _e: self.desenhar())
        self.cmb_tipo.bind("<<ComboboxSelected>>", lambda _e: self._trocar_tipo())
        for combo in (self.cmb_x, self.cmb_y, self.cmb_cor):
            combo.bind("<<ComboboxSelected>>", lambda _e: self.desenhar())

        self.btn_salvar = ttk.Button(lateral, text="Salvar imagem...", command=self.salvar)
        self.btn_salvar.pack(side="bottom", fill="x")

        principal = ttk.Frame(self, padding=(16, 16, 16, 8))
        principal.pack(side="left", fill="both", expand=True)
        self.abas = ttk.Notebook(principal)
        self.abas.pack(fill="both", expand=True)

        aba_grafico = tk.Frame(self.abas, bg=gr.TEMA["fundo"])
        self.figura = Figure(figsize=(8, 5.5), dpi=100, facecolor=gr.TEMA["fundo"])
        self.canvas = FigureCanvasTkAgg(self.figura, master=aba_grafico)
        barra = NavigationToolbar2Tk(self.canvas, aba_grafico, pack_toolbar=False)
        barra.configure(background=CORES["painel"])
        for filho in barra.winfo_children():
            try:
                filho.configure(background=CORES["painel"])
            except tk.TclError:
                pass
        barra.update()
        barra.pack(side="bottom", fill="x")
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.abas.add(aba_grafico, text="Gráfico")

        aba_tabela = ttk.Frame(self.abas, padding=10)
        self._montar_tabela(aba_tabela)
        self.abas.add(aba_tabela, text="Tabela")

        aba_funcoes = ttk.Frame(self.abas, padding=10)
        self._montar_funcoes(aba_funcoes)
        self.abas.add(aba_funcoes, text="Funções matemáticas")

        self.lbl_status = ttk.Label(principal, text="Abra uma planilha ou use o exemplo para começar.",
                                    style="Suave.TLabel")
        self.lbl_status.pack(anchor="w", pady=(6, 0))
        self._mensagem_inicial()
        self._trocar_tipo(desenhar=False)

    def _campo(self, pai, rotulo, variavel, valores) -> ttk.Combobox:
        ttk.Label(pai, text=rotulo, style="PainelSuave.TLabel").pack(anchor="w", pady=(8, 2))
        combo = ttk.Combobox(pai, textvariable=variavel, values=valores, state="readonly")
        combo.pack(fill="x")
        return combo

    def _mensagem_inicial(self) -> None:
        eixo = gr.novo_eixo(self.figura)
        eixo.axis("off")
        eixo.text(0.5, 0.55, "Abra uma planilha (.csv ou .xlsx)", ha="center", color=gr.TEMA["texto"],
                  fontsize=15, transform=eixo.transAxes)
        eixo.text(0.5, 0.45, "ou clique em \"Usar exemplo\"", ha="center", color=gr.TEMA["texto_suave"],
                  fontsize=11, transform=eixo.transAxes)
        self.canvas.draw_idle()

    def status(self, texto: str, cor: str = "texto_suave") -> None:
        self.lbl_status.configure(text=texto, foreground=CORES[cor])

    # ------------------------------------------------------------------ dados

    def abrir(self) -> None:
        caminho = filedialog.askopenfilename(parent=self, title="Abrir planilha",
                                             filetypes=[("Planilhas", "*.csv *.xlsx *.xls"), ("Todos", "*.*")])
        if not caminho:
            return
        try:
            df = dd.carregar(caminho)
        except dd.ErroDados as erro:
            messagebox.showerror("Não foi possível abrir", str(erro), parent=self)
            return
        self._usar(df, Path(caminho).name)

    def usar_exemplo(self) -> None:
        self._usar(dd.gerar_exemplo(), "Exemplo: 1500 clientes de crédito FICTÍCIOS, gerados por código")
        self.var_tipo.set("Dispersão")
        self.var_x.set("renda_mensal")
        self.var_y.set("limite_credito")
        self.var_cor.set("inadimplente")
        self._trocar_tipo()

    def _usar(self, df: pd.DataFrame, descricao: str) -> None:
        self.df = df
        self.colunas = dd.classificar(df)
        self.lbl_arquivo.configure(text=f"{descricao}\n{len(df)} linhas · {len(df.columns)} colunas")
        self.var_x.set("")
        self.var_y.set("")
        self.var_cor.set(NENHUMA)
        self._preencher_tabela()
        self._trocar_tipo()

    # ------------------------------------------------------------------ gráfico

    def _trocar_tipo(self, desenhar: bool = True) -> None:
        tipo = gr.TIPOS[self.var_tipo.get()]
        self.lbl_dica.configure(text=tipo.dica)
        opcoes = {"numerica": self.colunas.numericas, "categorica": self.colunas.categoricas}

        def ajustar(combo, variavel, requisito, extras=()):
            if requisito is None:
                combo.configure(values=[], state="disabled")
                variavel.set("")
                return
            valores = [*extras, *opcoes[requisito]]
            combo.configure(values=valores, state="readonly")
            if variavel.get() not in valores:
                variavel.set(valores[0] if valores else "")

        ajustar(self.cmb_x, self.var_x, tipo.precisa_x)
        ajustar(self.cmb_y, self.var_y, tipo.precisa_y, (CONTAGEM,) if tipo.y_opcional else ())
        if tipo.usa_cor:
            self.cmb_cor.configure(values=[NENHUMA, *self.colunas.categoricas], state="readonly")
        else:
            self.cmb_cor.configure(state="disabled")
            self.var_cor.set(NENHUMA)
        if tipo.precisa_y == "numerica" and self.var_y.get() == self.var_x.get() and len(opcoes["numerica"]) > 1:
            outras = [c for c in opcoes["numerica"] if c != self.var_x.get()]
            self.var_y.set(outras[0])
        if desenhar:
            self.desenhar()

    def desenhar(self) -> None:
        if self.df is None:
            return
        y = self.var_y.get()
        cor = self.var_cor.get()
        try:
            nota = gr.desenhar(self.figura, self.df, self.var_tipo.get(), x=self.var_x.get() or None,
                               y=None if y in ("", CONTAGEM) else y, cor=None if cor == NENHUMA else cor,
                               titulo=self.var_titulo.get().strip())
        except gr.ErroGrafico as erro:
            self.status(str(erro).capitalize(), "ambar")
            return
        self.canvas.draw_idle()
        self.abas.select(0)
        self.status(nota)

    def salvar(self) -> None:
        caminho = filedialog.asksaveasfilename(parent=self, title="Salvar gráfico", defaultextension=".png",
                                               initialfile="grafico.png",
                                               filetypes=[("PNG", "*.png"), ("SVG", "*.svg"), ("PDF", "*.pdf")])
        if caminho:
            self.figura.savefig(caminho, dpi=200, facecolor=self.figura.get_facecolor())
            self.status(f"Gráfico salvo em {caminho}", "verde")

    # ------------------------------------------------------------------ tabela

    def _montar_tabela(self, aba) -> None:
        self.lbl_tabela = ttk.Label(aba, text="", style="Suave.TLabel")
        self.lbl_tabela.pack(anchor="w", pady=(0, 6))
        quadro = ttk.Frame(aba)
        quadro.pack(fill="both", expand=True)
        self.tabela = ttk.Treeview(quadro, show="headings")
        rolagem_y = ttk.Scrollbar(quadro, orient="vertical", command=self.tabela.yview)
        rolagem_x = ttk.Scrollbar(quadro, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=rolagem_y.set, xscrollcommand=rolagem_x.set)
        rolagem_y.pack(side="right", fill="y")
        rolagem_x.pack(side="bottom", fill="x")
        self.tabela.pack(fill="both", expand=True)
        ttk.Label(aba, text="Resumo das colunas", style="Suave.TLabel").pack(anchor="w", pady=(10, 6))
        self.tabela_resumo = ttk.Treeview(aba, show="headings", height=8)
        self.tabela_resumo.pack(fill="x")

    @staticmethod
    def _texto(valor) -> str:
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            return ""
        if isinstance(valor, (float, np.floating)):
            return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(valor)

    def _preencher(self, arvore: ttk.Treeview, df: pd.DataFrame) -> None:
        arvore.delete(*arvore.get_children())
        colunas = list(df.columns)
        arvore.configure(columns=colunas)
        for coluna in colunas:
            numerica = pd.api.types.is_numeric_dtype(df[coluna])
            arvore.heading(coluna, text=coluna, anchor="e" if numerica else "w")
            maior = max([len(str(coluna)), *(len(self._texto(v)) for v in df[coluna].head(50))])
            arvore.column(coluna, width=max(70, min(240, maior * 8 + 16)), anchor="e" if numerica else "w",
                          stretch=False)
        for linha in df.itertuples(index=False):
            arvore.insert("", "end", values=[self._texto(v) for v in linha])

    def _preencher_tabela(self) -> None:
        df = self.df
        self._preencher(self.tabela, df.head(MAX_LINHAS_TABELA))
        extra = f" (mostrando as primeiras {MAX_LINHAS_TABELA})" if len(df) > MAX_LINHAS_TABELA else ""
        self.lbl_tabela.configure(text=f"{len(df)} linhas{extra}")
        self._preencher(self.tabela_resumo, dd.resumo(df))

    # ------------------------------------------------------------------ funções

    def _montar_funcoes(self, aba) -> None:
        painel = tk.Frame(aba, bg=CORES["painel"], padx=16, pady=14)
        painel.pack(fill="x")
        tk.Label(painel, text="Escreva até 3 funções de x, como na aula: sen(πx), sen(2πx), x² − 3x + 2...",
                 bg=CORES["painel"], fg=CORES["texto_suave"]).grid(row=0, column=0, columnspan=6, sticky="w")
        self.vars_funcao = [tk.StringVar(value=v) for v in ("sen(pi x)", "sen(2 pi x)", "")]
        for i, var in enumerate(self.vars_funcao):
            tk.Label(painel, text=f"f{i + 1}(x) =", bg=CORES["painel"], fg=gr.CATEGORICAS[i],
                     font=(FONTE, 10, "bold")).grid(row=1 + i, column=0, sticky="w", pady=3)
            entrada = ttk.Entry(painel, textvariable=var, width=42)
            entrada.grid(row=1 + i, column=1, sticky="w", padx=8, ipady=2)
            entrada.bind("<Return>", lambda _e: self.desenhar_funcoes())
        self.var_xmin, self.var_xmax = tk.StringVar(value="0"), tk.StringVar(value="2")
        tk.Label(painel, text="x de", bg=CORES["painel"], fg=CORES["texto_suave"]).grid(row=1, column=2, padx=(16, 4))
        ttk.Entry(painel, textvariable=self.var_xmin, width=7).grid(row=1, column=3)
        tk.Label(painel, text="até", bg=CORES["painel"], fg=CORES["texto_suave"]).grid(row=1, column=4, padx=4)
        ttk.Entry(painel, textvariable=self.var_xmax, width=7).grid(row=1, column=5)
        ttk.Button(painel, text="Desenhar funções", style="Destaque.TButton",
                   command=self.desenhar_funcoes).grid(row=3, column=2, columnspan=4, sticky="e")
        tk.Label(aba, text="Funções: sen, cos, tan, exp, ln, log, raiz, abs · constantes: π (pi), e · "
                           "potência: ^ · o gráfico aparece na aba Gráfico.",
                 bg=CORES["fundo"], fg=CORES["texto_suave"]).pack(anchor="w", pady=10)

    def desenhar_funcoes(self) -> None:
        try:
            inicio = float(self.var_xmin.get().replace(",", "."))
            fim = float(self.var_xmax.get().replace(",", "."))
            if inicio >= fim:
                raise ValueError
        except ValueError:
            self.status("Intervalo inválido: o início precisa ser menor que o fim.", "ambar")
            return
        x = np.linspace(inicio, fim, 800)
        curvas = []
        for var in self.vars_funcao:
            texto = var.get().strip()
            if not texto:
                continue
            try:
                curvas.append((texto, x, fn.avaliar(texto, x)))
            except fn.ErroFuncao as erro:
                self.status(f"f(x) = {texto}: {erro}", "ambar")
                return
        if not curvas:
            self.status("Escreva pelo menos uma função.", "ambar")
            return
        gr.desenhar_funcoes(self.figura, curvas)
        self.canvas.draw_idle()
        self.abas.select(0)
        self.status(f"{len(curvas)} função(ões) de x = {inicio:g} até {fim:g}")

    def _fechar(self) -> None:
        self.quit()
        self.destroy()


def main() -> None:
    Aplicativo().mainloop()


if __name__ == "__main__":
    main()
