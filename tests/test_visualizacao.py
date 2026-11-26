import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dados as dd  # noqa: E402
import funcoes as fn  # noqa: E402
import graficos as gr  # noqa: E402


class TestDados(unittest.TestCase):
    def test_exemplo_e_reprodutivel(self):
        a, b = dd.gerar_exemplo(300), dd.gerar_exemplo(300)
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(len(a), 300)
        self.assertTrue((a["pagamento_medio"] >= 0).all())
        self.assertTrue((a["fatura_media"] <= a["limite_credito"]).all())
        self.assertEqual(set(a["inadimplente"]), {"Sim", "Não"})

    def test_exemplo_tem_relacoes(self):
        df = dd.gerar_exemplo()
        # quem atrasa mais tende a ser inadimplente
        media = df.groupby("inadimplente")["meses_em_atraso"].mean()
        self.assertGreater(media["Sim"], media["Não"])

    def test_classificar(self):
        df = dd.gerar_exemplo(200)
        colunas = dd.classificar(df)
        self.assertIn("renda_mensal", colunas.numericas)
        self.assertNotIn("renda_mensal", colunas.categoricas)
        self.assertIn("sexo", colunas.categoricas)
        # coluna numérica com poucos valores serve para os dois papéis
        self.assertIn("meses_em_atraso", colunas.numericas)
        self.assertIn("meses_em_atraso", colunas.categoricas)

    def test_csv_brasileiro_e_coluna_de_indice(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.csv"
            arquivo.write_text(";nome;valor\n0;Ana;1,5\n1;Bia;2,25\n", encoding="cp1252")
            df = dd.carregar(arquivo)
            self.assertEqual(list(df.columns), ["nome", "valor"])
            self.assertEqual(df["valor"].tolist(), [1.5, 2.25])

    def test_xlsx(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.xlsx"
            dd.gerar_exemplo(50).to_excel(arquivo)  # salva com o índice, como na aula
            df = dd.carregar(arquivo)
            self.assertNotIn("Unnamed: 0", df.columns)
            self.assertEqual(len(df), 50)

    def test_formato_invalido(self):
        with self.assertRaises(dd.ErroDados):
            dd.carregar("dados.json")

    def test_resumo(self):
        resumo = dd.resumo(pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "x"]})).set_index("coluna")
        self.assertEqual(resumo.loc["a", "vazios"], 1)
        self.assertEqual(resumo.loc["a", "média"], 1.5)
        self.assertEqual(resumo.loc["b", "tipo"], "texto")


class TestFuncoes(unittest.TestCase):
    x = np.linspace(-2, 2, 9)

    def test_formas_de_escrever(self):
        casos = {
            "x^2 - 3x + 2": self.x ** 2 - 3 * self.x + 2,
            "sen(pi*x)": np.sin(np.pi * self.x),
            "sen(2πx)": np.sin(2 * np.pi * self.x),
            "exp(-x)": np.exp(-self.x),
            "xsen(x)": self.x * np.sin(self.x),
            "2(x+1)": 2 * (self.x + 1),
            "abs(x)": np.abs(self.x),
            "5": np.full_like(self.x, 5),
        }
        for texto, esperado in casos.items():
            np.testing.assert_allclose(fn.avaliar(texto, self.x), esperado, err_msg=texto)

    def test_fora_do_dominio_vira_lacuna(self):
        y = fn.avaliar("raiz(x)", self.x)
        self.assertTrue(np.isnan(y[0]))
        self.assertEqual(y[-1], np.sqrt(2))
        self.assertTrue(np.isnan(fn.avaliar("1/x", np.array([0.0]))[0]))

    def test_rejeita_codigo(self):
        for texto in ("", "x +", "__import__('os')", "y + 1", "x.real", "open('a')", "x ** 99999"):
            with self.assertRaises(fn.ErroFuncao, msg=texto):
                fn.avaliar(texto, self.x)


class TestGraficos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = dd.gerar_exemplo(400)

    def desenhar(self, tipo, **kwargs):
        figura = Figure()
        nota = gr.desenhar(figura, self.df, tipo, **kwargs)
        self.assertTrue(nota)
        return figura

    def test_todos_os_tipos(self):
        self.desenhar("Dispersão", x="renda_mensal", y="limite_credito", cor="inadimplente")
        self.desenhar("Linha", x="idade", y="fatura_media", cor="sexo")
        self.desenhar("Histograma", x="idade")
        self.desenhar("Histograma", x="idade", cor="escolaridade")
        self.desenhar("Barras", x="escolaridade", y="renda_mensal")
        self.desenhar("Barras", x="estado_civil")
        self.desenhar("Caixa (boxplot)", x="estado_civil", y="limite_credito")
        self.desenhar("Violino", x="sexo", y="limite_credito")
        self.desenhar("Correlação")

    def test_titulo_padrao(self):
        figura = self.desenhar("Barras", x="estado_civil")
        self.assertEqual(figura.axes[0].get_title(loc="left"), "Quantidade por estado_civil")

    def test_barras_rotulos_dos_eixos(self):
        eixo = self.desenhar("Barras", x="escolaridade", y="renda_mensal").axes[0]
        self.assertEqual(eixo.get_xlabel(), "renda_mensal")
        self.assertEqual(eixo.get_ylabel(), "escolaridade")

    def test_dispersao_limita_cores(self):
        figura = self.desenhar("Dispersão", x="renda_mensal", y="limite_credito", cor="escolaridade")
        rotulos = [t.get_text() for t in figura.axes[0].get_legend().get_texts()]
        self.assertLessEqual(len(rotulos), gr.LIMITE_DISPERSAO)

    def test_cor_segue_a_categoria(self):
        serie = pd.Series(["b", "a", "c", "a"])
        _, cores = gr.agrupar_categorias(serie, 8)
        _, cores_filtradas = gr.agrupar_categorias(serie[serie != "c"], 8)
        self.assertEqual(cores["a"], cores_filtradas["a"])
        self.assertEqual(cores["a"], gr.CATEGORICAS[0])

    def test_outros(self):
        serie = pd.Series([str(i) for i in range(10)] * 3 + ["0"] * 5)
        agrupada, cores = gr.agrupar_categorias(serie, 3)
        self.assertEqual(set(agrupada), {"0", "1", "Outros"})
        self.assertEqual(cores["Outros"], gr.TEMA["outros"])

    def test_erros(self):
        with self.assertRaises(gr.ErroGrafico):
            gr.desenhar(Figure(), self.df, "Dispersão", x="renda_mensal")
        with self.assertRaises(gr.ErroGrafico):
            gr.desenhar(Figure(), self.df, "Histograma", x="sexo")
        with self.assertRaises(gr.ErroGrafico):
            gr.desenhar(Figure(), pd.DataFrame({"a": ["x"]}), "Correlação")

    def test_funcoes(self):
        figura = Figure()
        x = np.linspace(0, 2, 50)
        gr.desenhar_funcoes(figura, [("sen(πx)", x, np.sin(np.pi * x)), ("sen(2πx)", x, np.sin(2 * np.pi * x))])
        self.assertEqual(len(figura.axes[0].get_legend().get_texts()), 2)


if __name__ == "__main__":
    unittest.main()
