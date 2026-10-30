-- This is a connectivity fixture, not a complete i2b2 schema.
-- Replace it with the agreed synthetic schema before evaluation.

CREATE TABLE public.patient_dimension (
    patient_num BIGINT PRIMARY KEY
);

INSERT INTO public.patient_dimension (patient_num)
SELECT generate_series(1, 20);