
class MobileTemplateMixin:
    """
    Mixin to switch template to mobile version if request.is_mobile is True.
    Expects 'mobile_template_name' to be defined on the view, 
    or appends '_mobile' to the base template name before extension.
    """
    mobile_template_name = None

    def get_template_names(self):
        names = super().get_template_names()
        if getattr(self.request, 'is_mobile', False):
            if self.mobile_template_name:
                return [self.mobile_template_name]
            
            # Fallback: try to find a mobile version of the first template
            # e.g., 'target_list.html' -> 'mobile/target_list_mobile.html'
            # But simpler transparency: User sets mobile_template_name explicitly.
        return names
