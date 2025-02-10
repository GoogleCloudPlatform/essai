# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import StrEnum, Enum


# response enums
class ProcessStatus(StrEnum):
    DONE = "DONE"
    NOT_DONE = "IN_PROGRESS"


class Grade(Enum):
    excellent = 200
    good = 160
    average = 120
    insufficient = 80
    precarious = 40
    ignorance = 0


class EssayValidation(StrEnum):
    VALID = "Valid"
    UNREA = "Inválida - Texto Ilegível ou Ininteligível"
    DESVIO_GENERO = "Inválida - Desvio do Gênero Dissertativo-Argumentativo"
    COPIA_TEXTO_MOTIVADOR = "Inválida - Cópia dos textos motivadores"
    VIOLACAO_DIREITOS_HUMANOS = "Inválida - Violação aos Direitos Humanos"


# feedback
class NStars(Enum):
    UM: 1
    DOIS: 2
    TRES: 3
    QUATRO: 4
    CINCO: 5
    SEIS: 6
    SETE: 7
    OITO: 8
    NOVE: 9
    DEZ: 10
