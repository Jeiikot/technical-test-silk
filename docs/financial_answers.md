# Parte 4 – Respuestas financieras y contables

## 4.1 Preguntas teóricas

**Nominal vs efectiva — conversión 24% NMV a EA**

La tasa nominal (NMV) divide el año en 12 periodos sin capitalizar. La efectiva (EA) ya incluye el efecto del interés compuesto. Para convertir 24% NMV:

```
i_mensual = 24% / 12 = 2%
EA = (1 + 0.02)^12 - 1 = 26.82% EA
```

---

**Interés simple vs compuesto**

Simple: los intereses siempre se calculan sobre el capital original. Compuesto: los intereses se acumulan al saldo y el siguiente periodo se cobran sobre más capital.

Los créditos de consumo en Colombia usan interés compuesto — cuota fija es sistema francés, abono constante es sistema alemán.

---

**Partida doble — cuentas PUC**

Cada movimiento afecta mínimo dos cuentas por el mismo valor: débito = crédito.

a) Desembolso $10.000.000:

| Código | Cuenta | Débito | Crédito |
|---|---|---|---|
| 141005 | Cartera consumo – Capital | 10.000.000 | |
| 111005 | Disponible – Bancos | | 10.000.000 |

b) Causación intereses mes 1 (2% sobre $10M = $200.000):

| Código | Cuenta | Débito | Crédito |
|---|---|---|---|
| 270505 | Intereses por cobrar | 200.000 | |
| 411005 | Ingresos por intereses | | 200.000 |

c) Recaudo primera cuota ($946.020 capital + $200.000 interés):

| Código | Cuenta | Débito | Crédito |
|---|---|---|---|
| 111005 | Disponible – Bancos | 1.146.020 | |
| 270505 | Intereses por cobrar | | 200.000 |
| 141005 | Cartera consumo – Capital | | 946.020 |

---

**Provisión de cartera**

Es el gasto que reconoce la probabilidad de no recuperar parte de la cartera. La SFC define porcentajes por categoría de riesgo:

- A (normal): 1%
- B (aceptable): 3.2%
- C (apreciable): 20%
- D (significativo): 50%
- E (irrecuperable): 100%

En el modelo, la columna `risk_class` en `clients` soporta esta clasificación. El asiento sería débito 519900 Gasto provisiones / crédito 149900 Provisión cartera.

---

**Causación vs caja**

Caja: registra cuando entra o sale plata. Causación: registra cuando se genera el hecho económico, independiente de si se cobró.

Un sistema de créditos necesita causación porque los intereses se generan día a día aunque el cliente no pague. Sin causación, un mes sin pagos mostraría cero ingresos, lo cual no refleja la realidad del negocio.

---

**Tasa de usura**

Es la tasa máxima legal que se puede cobrar en Colombia para créditos de libre asignación. La certifica la Superintendencia Financiera cada trimestre. Cobrar por encima es delito de usura con pena privativa de la libertad. Para entidades vigiladas por la SFC también aplica sanción administrativa.

---

## 4.2 Ejercicio práctico

**Datos:** $20.000.000 COP | 24% NMV | 12 meses | cuota fija | desembolso 01-mar-2026

### Tasa mensual y verificación de usura

```
i_mensual = 24% / 12 = 2% = 0.02
EA = (1.02)^12 - 1 = 26.82% EA

Usura asumida: 27.62% EA
26.82% < 27.62% → válido
```

### Cuota fija

```
C = 20.000.000 × [0.02 × (1.02)^12] / [(1.02)^12 - 1]
  = 20.000.000 × 0.025365 / 0.268242
  = $1.891.195 COP (aprox.)
```

### Tabla de amortización

| # | Saldo inicial | Interés 2% | Capital | Cuota | Saldo final |
|---|---|---|---|---|---|
| 1 | 20.000.000,00 | 400.000,00 | 1.491.195,03 | 1.891.195,03 | 18.508.804,97 |
| 2 | 18.508.804,97 | 370.176,10 | 1.521.018,93 | 1.891.195,03 | 16.987.786,04 |
| 3 | 16.987.786,04 | 339.755,72 | 1.551.439,31 | 1.891.195,03 | 15.436.346,73 |
| 4 | 15.436.346,73 | 308.726,93 | 1.582.468,10 | 1.891.195,03 | 13.853.878,63 |
| 5 | 13.853.878,63 | 277.077,57 | 1.614.117,46 | 1.891.195,03 | 12.239.761,17 |
| 6 | 12.239.761,17 | 244.795,22 | 1.646.399,81 | 1.891.195,03 | 10.593.361,36 |
| 7 | 10.593.361,36 | 211.867,23 | 1.679.327,80 | 1.891.195,03 | 8.914.033,56 |
| 8 | 8.914.033,56 | 178.280,67 | 1.712.914,36 | 1.891.195,03 | 7.201.119,20 |
| 9 | 7.201.119,20 | 144.022,38 | 1.747.172,65 | 1.891.195,03 | 5.453.946,55 |
| 10 | 5.453.946,55 | 109.078,93 | 1.782.116,10 | 1.891.195,03 | 3.671.830,45 |
| 11 | 3.671.830,45 | 73.436,61 | 1.817.758,42 | 1.891.195,03 | 1.854.072,03 |
| 12 | 1.854.072,03 | 37.081,44 | 1.854.072,03 | 1.891.153,47* | 0,00 |

*Última cuota ajustada por redondeo acumulado.

Total intereses: ~$2.694.298 COP  
Total pagado: ~$22.694.298 COP

### Interés moratorio cuota 6 — 15 días de atraso

```
Saldo en mora = $10.593.361,36
Tasa mora = 2% × 1.5 = 3% mensual

Interés moratorio = 10.593.361,36 × (0.03/30) × 15 = $158.900,42 COP
```

Total a pagar: $1.891.195,03 + $158.900,42 = **$2.050.095,45**

### Asientos contables PUC

**Desembolso ($20.000.000):**

| Código | Cuenta | Débito | Crédito |
|---|---|---|---|
| 141005 | Cartera créditos consumo | $20.000.000 | |
| 111005 | Disponible – Bancos | | $20.000.000 |

**Recaudo primera cuota ($400.000 interés + $1.491.195,03 capital):**

| Código | Cuenta | Débito | Crédito |
|---|---|---|---|
| 111005 | Disponible – Bancos | $1.891.195,03 | |
| 270505 | Intereses por cobrar | | $400.000,00 |
| 141005 | Cartera consumo | | $1.491.195,03 |
