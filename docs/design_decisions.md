# Parte 1 – Decisiones de diseño y preguntas conceptuales

## Decisiones de diseño

**NUMERIC(18,2) para montos en COP**

`FLOAT` no puede representar exactamente fracciones decimales. Ejemplo:

```python
>>> 1_000_000.0 * 0.02
19999.999999999996   # debería ser 20000.00
```

Con `NUMERIC(18,2)` PostgreSQL garantiza la precisión. En Python uso `decimal.Decimal` por la misma razón.

**Tasas almacenadas como EA**

Sin importar si el cliente ingresa NMV o EA, todo se convierte a EA antes de guardar. Así la verificación de usura y cualquier comparación de tasas siempre trabaja con el mismo formato.

**UNIQUE(payment_reference) para idempotencia PSE**

Las pasarelas reenvían callbacks cuando hay timeouts. Con la constraint única, el segundo INSERT falla con `IntegrityError` y la app devuelve 409 sin tocar los saldos.

**CHECK(debit_amount = credit_amount) en accounting_entries**

La partida doble garantizada a nivel de BD, no solo en la app. Si algo falla a nivel de código, la BD rechaza el asiento descuadrado.

**Índice parcial en cuotas pendientes**

```sql
CREATE INDEX idx_amort_unpaid_due ON amortization_schedule (due_date) WHERE NOT is_paid;
```

Las consultas de mora siempre filtran por cuotas sin pagar. Un índice parcial es más pequeño y rápido que uno sobre toda la tabla.

---

## Preguntas conceptuales

### ¿Por qué NUMERIC(18,2) y no FLOAT?

Ya explicado arriba. Resumiendo: FLOAT es para cálculos científicos donde pequeños errores son aceptables. Para dinero, necesitamos exactitud — un centavo de diferencia en miles de créditos rompe la conciliación contable.

### Concurrencia en pagos simultáneos PSE + corresponsal

Si dos transacciones leen el mismo saldo al mismo tiempo, los dos podrían decrementarlo por el mismo pago. La solución:

1. `SELECT ... FOR UPDATE` al inicio del registro de pago — la segunda transacción espera a que la primera termine.
2. `UNIQUE(payment_reference)` — si el mismo callback llega dos veces, el segundo falla antes de modificar nada.

### Partida doble y el PUC

Cada movimiento económico afecta mínimo dos cuentas por el mismo valor: lo que entra por un lado sale por otro. En el modelo, cada fila de `accounting_entries` tiene `debit_amount = credit_amount`, garantizado por un CHECK en la BD.

Tres cuentas que uso:

| Código | Cuenta | Uso |
|---|---|---|
| 141005 | Cartera consumo – Capital | Sube al desembolsar, baja con pagos de capital |
| 270505 | Intereses por cobrar | Sube con causación mensual, baja al recaudar |
| 411005 | Ingresos por intereses | Crédito en cada causación |
