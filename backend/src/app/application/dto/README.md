# application/dto

Objetos de transferencia de datos usados entre casos de uso y sus llamadores (los entrypoints de infraestructura), distintos de las entidades de dominio.

Por qué existen por separado de las entidades: un DTO representa la forma en que un caso de uso recibe una solicitud o entrega un resultado (p. ej. `AnswerQueryRequest`, `AnswerQueryResponse`), mientras que una entidad de dominio (`Conversation`, `Message`) representa un concepto del negocio con sus propias invariantes. Mezclarlos acoplaría el modelo de dominio a la forma específica en que el API HTTP serializa datos.
