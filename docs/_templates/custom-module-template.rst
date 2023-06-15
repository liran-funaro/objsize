{{ fullname | escape | underline}}

.. automodule:: {{ fullname }}
   :members:
   {% block modules %}
   {% if modules %}
   .. rubric:: {{ _('Sub Modules') }}
   .. autosummary::
      :toctree:
      :template: custom-module-template.rst
      :recursive:
   {% for item in modules %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   .. rubric:: {{ _('Classes and Functions') }}
