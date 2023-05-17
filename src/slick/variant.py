class Variant:
    def __init__(self, name, default, description, values, multi, validator, sticky):
        self.name = name
        self.default = default
        self.description = description
        self.values = values
        self.multi = multi
        self.validator = validator
        self.sticky = sticky
