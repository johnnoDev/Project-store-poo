from django.core.exceptions import ValidationError


def validate_cedula_ec(value):
    value = str(value).strip()
    if len(value) not in (10, 13):
        raise ValidationError('La cédula debe tener 10 dígitos o el RUC 13 dígitos.')
    if not value.isdigit():
        raise ValidationError('Solo se permiten dígitos.')

    province = int(value[:2])
    if province < 1 or province > 24:
        raise ValidationError('Código de provincia inválido (01-24).')

    third_digit = int(value[2])
    if third_digit >= 6:
        raise ValidationError('El tercer dígito debe ser menor a 6 para personas naturales.')

    coefficients = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for i, coef in enumerate(coefficients):
        digit = int(value[i]) * coef
        if digit >= 10:
            digit -= 9
        total += digit

    verifier = int(value[9])
    remainder = total % 10
    check = 0 if remainder == 0 else 10 - remainder

    if check != verifier:
        raise ValidationError('Cédula/RUC inválido. El dígito verificador no coincide.')
