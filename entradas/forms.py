from django import forms

from .models import PedidoEntrada, QuestionarioEntrada, PerfilNKATA


class PedidoEntradaForm(forms.ModelForm):
    class Meta:
        model = PedidoEntrada
        fields = [
            "nome_completo",
            "email",
            "telefone",
            "idade",
            "cidade",
            "genero",
            "objetivo",
            "aceita_verificacao",
            "foto_perfil",
            "foto_extra_1",
            "foto_extra_2",
            "foto_extra_3",
            "bi_frente",
            "bi_verso",
            "selfie_com_bi",
        ]

        widgets = {
            "nome_completo": forms.TextInput(attrs={
                "placeholder": "Digite o seu nome completo",
                "autocomplete": "name",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Digite o seu email",
                "autocomplete": "email",
            }),
            "telefone": forms.TextInput(attrs={
                "placeholder": "+258...",
                "autocomplete": "tel",
            }),
            "idade": forms.NumberInput(attrs={
                "placeholder": "Ex: 28",
                "min": "18",
            }),
            "cidade": forms.TextInput(attrs={
                "placeholder": "Ex: Maputo",
                "autocomplete": "address-level2",
            }),
            "foto_perfil": forms.FileInput(attrs={
                "accept": "image/*",
            }),
            "foto_extra_1": forms.FileInput(attrs={
                "accept": "image/*",
            }),
            "foto_extra_2": forms.FileInput(attrs={
                "accept": "image/*",
            }),
            "foto_extra_3": forms.FileInput(attrs={
                "accept": "image/*",
            }),
            "bi_frente": forms.FileInput(attrs={
                "accept": "image/*",
            }),
            "bi_verso": forms.FileInput(attrs={
                "accept": "image/*",
            }),
            "selfie_com_bi": forms.FileInput(attrs={
                "accept": "image/*",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # O novo frontend entrega estes ficheiros através da sessão NKATA ID.
        # Permanecem opcionais aqui para compatibilidade com pedidos antigos.
        for field_name in ("bi_frente", "bi_verso", "selfie_com_bi"):
            self.fields[field_name].required = False

        self.fields["genero"].choices = [
            ("", "Selecione o género")
        ] + list(PedidoEntrada.GENERO_CHOICES)

        self.fields["objetivo"].choices = [
            ("", "Selecione o que procura")
        ] + list(PedidoEntrada.OBJETIVO_CHOICES)

    def clean_idade(self):
        idade = self.cleaned_data.get("idade")

        if idade is not None and idade < 18:
            raise forms.ValidationError(
                "O NKATA é apenas para adultos com 18 anos ou mais."
            )

        return idade

    def clean_aceita_verificacao(self):
        aceita = self.cleaned_data.get("aceita_verificacao")

        if not aceita:
            raise forms.ValidationError(
                "Para solicitar entrada no NKATA, deve aceitar passar por verificação."
            )

        return aceita


class QuestionarioEntradaForm(forms.ModelForm):
    class Meta:
        model = QuestionarioEntrada
        fields = [
            "disponibilidade",
            "tem_filhos",
            "aceita_pessoa_com_filhos",
            "cidade_preferida",
            "faixa_etaria_preferida",
            "sobre_si",
            "o_que_valoriza",
            "o_que_nao_aceita",
            "aceita_regras",
        ]

        widgets = {
            "cidade_preferida": forms.TextInput(attrs={
                "placeholder": "Ex: Maputo, Matola, Vilankulo..."
            }),
            "faixa_etaria_preferida": forms.TextInput(attrs={
                "placeholder": "Ex: 25 a 35 anos"
            }),
            "sobre_si": forms.Textarea(attrs={
                "placeholder": "Fale um pouco sobre si...",
                "rows": 4
            }),
            "o_que_valoriza": forms.Textarea(attrs={
                "placeholder": "Ex: respeito, honestidade, comunicação...",
                "rows": 4
            }),
            "o_que_nao_aceita": forms.Textarea(attrs={
                "placeholder": "Ex: mentiras, agressividade, falta de respeito...",
                "rows": 4
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["disponibilidade"].choices = [
            ("", "Selecione uma opção")
        ] + list(QuestionarioEntrada.DISPONIBILIDADE_CHOICES)

        self.fields["tem_filhos"].choices = [
            ("", "Selecione uma opção")
        ] + list(QuestionarioEntrada.FILHOS_CHOICES)

        self.fields["aceita_pessoa_com_filhos"].choices = [
            ("", "Selecione uma opção")
        ] + list(QuestionarioEntrada.ACEITA_FILHOS_CHOICES)

    def clean_aceita_regras(self):
        aceita = self.cleaned_data.get("aceita_regras")

        if not aceita:
            raise forms.ValidationError(
                "Para continuar, deve aceitar as regras da comunidade NKATA."
            )

        return aceita


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = PerfilNKATA
        fields = [
            "nome_publico",
            "cidade",
            "objetivo",
            "sobre_si",
            "o_que_valoriza",
            "o_que_nao_aceita",
        ]

        widgets = {
            "nome_publico": forms.TextInput(attrs={
                "placeholder": "Nome que aparecerá publicamente"
            }),
            "cidade": forms.TextInput(attrs={
                "placeholder": "Ex: Maputo, Matola, Vilankulo..."
            }),
            "sobre_si": forms.Textarea(attrs={
                "placeholder": "Fale um pouco sobre si...",
                "rows": 5
            }),
            "o_que_valoriza": forms.Textarea(attrs={
                "placeholder": "O que valoriza numa relação?",
                "rows": 5
            }),
            "o_que_nao_aceita": forms.Textarea(attrs={
                "placeholder": "O que não aceita numa relação?",
                "rows": 5
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["objetivo"].choices = [
            ("", "Selecione o que procura")
        ] + list(PedidoEntrada.OBJETIVO_CHOICES)

    def clean_nome_publico(self):
        nome = self.cleaned_data.get("nome_publico", "").strip()

        if len(nome) < 3:
            raise forms.ValidationError(
                "O nome público deve ter pelo menos 3 caracteres."
            )

        return nome

    def clean_sobre_si(self):
        texto = self.cleaned_data.get("sobre_si", "").strip()

        if len(texto) < 20:
            raise forms.ValidationError(
                "Fale um pouco mais sobre si. Use pelo menos 20 caracteres."
            )

        return texto
