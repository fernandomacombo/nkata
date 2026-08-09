from types import SimpleNamespace

from django.core.exceptions import ObjectDoesNotExist
from django.test import SimpleTestCase

from .account_lifecycle import (
    manter_perfil_privado_ate_conta_ficar_pronta,
    pedido_tem_questionario,
    perfil_pronto_para_publicar,
)


class PedidoSemQuestionario:
    status = "APROVADO"

    @property
    def questionario(self):
        raise ObjectDoesNotExist


class ContaFalsa:
    def __init__(self, senha_utilizavel):
        self._senha_utilizavel = senha_utilizavel

    def has_usable_password(self):
        return self._senha_utilizavel


class CicloDeAcessoTests(SimpleTestCase):
    def criar_perfil(self, *, senha_utilizavel, status_pedido="APROVADO", com_questionario=True):
        pedido = SimpleNamespace(status=status_pedido)
        if com_questionario:
            pedido.questionario = SimpleNamespace(pk=1)
        else:
            pedido = PedidoSemQuestionario()
            pedido.status = status_pedido

        return SimpleNamespace(
            usuario_id=1,
            usuario=ContaFalsa(senha_utilizavel),
            pedido=pedido,
            status="ATIVO",
            visivel=True,
        )

    def test_pedido_sem_questionario_nao_esta_completo(self):
        self.assertFalse(pedido_tem_questionario(PedidoSemQuestionario()))

    def test_perfil_sem_palavra_passe_fica_oculto(self):
        perfil = self.criar_perfil(senha_utilizavel=False)

        manter_perfil_privado_ate_conta_ficar_pronta(None, perfil)

        self.assertEqual(perfil.status, "PAUSADO")
        self.assertFalse(perfil.visivel)

    def test_perfil_de_pedido_nao_aprovado_fica_oculto(self):
        perfil = self.criar_perfil(
            senha_utilizavel=True,
            status_pedido="EM_ANALISE",
        )

        manter_perfil_privado_ate_conta_ficar_pronta(None, perfil)

        self.assertEqual(perfil.status, "PAUSADO")
        self.assertFalse(perfil.visivel)

    def test_perfil_bloqueado_nunca_fica_visivel(self):
        perfil = self.criar_perfil(senha_utilizavel=True)
        perfil.status = "BLOQUEADO"
        perfil.visivel = True

        manter_perfil_privado_ate_conta_ficar_pronta(None, perfil)

        self.assertEqual(perfil.status, "BLOQUEADO")
        self.assertFalse(perfil.visivel)

    def test_perfil_com_fluxo_completo_pode_ser_publicado(self):
        perfil = self.criar_perfil(senha_utilizavel=True)

        self.assertTrue(perfil_pronto_para_publicar(perfil))

        manter_perfil_privado_ate_conta_ficar_pronta(None, perfil)

        self.assertEqual(perfil.status, "ATIVO")
        self.assertTrue(perfil.visivel)
