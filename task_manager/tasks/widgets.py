from django import forms


class StatusSelectWidget(forms.Select):
    """Select widget that renders status colors on options.

    The colors mapping (status id -> hex color) is passed via the
    ``status_colors`` attribute, filled by TaskForm after the queryset
    is filtered by team/individual mode. Options without a color simply
    render without the attribute, so the form degrades gracefully.
    """

    def __init__(self, attrs=None, status_colors=None):
        super().__init__(attrs)
        self.status_colors = status_colors or {}

    def create_option(self, name, value, label, selected, index,
                      subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index,
            subindex=subindex, attrs=attrs
        )
        color = self.status_colors.get(value)
        if color:
            option['attrs']['data-color'] = color
        return option

    def __deepcopy__(self, memo):
        # forms are deep-copied in several places; the colors mapping
        # is read-only, a shallow copy is enough and cheaper
        obj = super().__deepcopy__(memo)
        obj.status_colors = dict(self.status_colors)
        return obj
