# domain/value_objects

Objetos inmutables sin identidad propia, definidos por sus atributos: p. ej. `EmailAddress` (con validación de dominio `@uvg.edu.gt`), `EmbeddingVector`, `SimilarityScore`, `VerificationConfidence`.

Reglas:
- Inmutables una vez creados.
- Encapsulan sus propias reglas de validación (p. ej. `EmailAddress` rechaza correos fuera del dominio institucional en su constructor, no en una capa externa).
