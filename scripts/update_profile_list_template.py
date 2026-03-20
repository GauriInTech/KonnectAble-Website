from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'profiles' / 'templates' / 'profiles' / 'profile_list.html'

new_content = '''{% extends "base.html" %}
{% load static %}

{% block content %}

<link rel="stylesheet" href="{% static 'css/profile.css' %}">

<div class="profile-list-page" style="padding:1rem">
  <h2 style="margin-bottom:1rem">Your Network</h2>

  {% if not request.user.is_authenticated %}
    <div class="empty-state" style="max-width:600px; margin:0 auto;">
      <p>You need to be logged in to see who you’re supporting and who supports you.</p>
      <p><a href="{% url 'login' %}">Log in</a> or <a href="{% url 'signup' %}">sign up</a> to start connecting.</p>
    </div>
  {% else %}
    <div class="follow-grid" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:1.25rem;">

      <section class="follow-section">
        <h3 style="margin-bottom:0.75rem">Supporters ({{ supporters|length }})</h3>
        {% if supporters %}
          <div class="profiles-container" role="list" aria-label="Supporters">
            {% for profile in supporters %}
              <div class="profile-card" role="listitem">
                <div class="profile-top">
                  <div class="profile-avatar">
                    {% if profile.profile_image %}
                      <img src="{{ profile.profile_image.url }}" alt="{{ profile.user.username }}" style="width:56px;height:56px;border-radius:12px;object-fit:cover" />
                    {% else %}
                      {{ profile.user.username|slice:"0:2"|upper }}
                    {% endif %}
                  </div>
                  <div class="profile-meta">
                    <p class="profile-username"><a class="profile-link" href="{% url 'profile_detail' profile.user.username %}">{{ profile.user.username }}</a></p>
                    <div class="profile-stats">Supporting: <strong>{{ profile.supports_count }}</strong> • Supporters: <strong>{{ profile.supporters_count }}</strong></div>
                  </div>
                </div>

                <div class="profile-actions">
                  {% if request.user.username != profile.user.username %}
                    <form method="post" action="{% url 'toggle_support' profile.user.username %}" style="display:inline" aria-label="Support {{ profile.user.username }}">
                      {% csrf_token %}
                      {% if profile.is_supported_by_me %}
                        <button type="submit" class="btn btn-primary" aria-pressed="true">Un-support</button>
                      {% else %}
                        <button type="submit" class="btn btn-primary" aria-pressed="false">Support</button>
                      {% endif %}
                    </form>
                  {% else %}
                    <a href="{% url 'profile_detail' profile.user.username %}" class="btn btn-ghost">View</a>
                  {% endif %}
                </div>
              </div>
            {% endfor %}
          </div>
        {% else %}
          <div class="empty-state">No one is supporting you yet. Start supporting people to build connections.</div>
        {% endif %}
      </section>

      <section class="follow-section">
        <h3 style="margin-bottom:0.75rem">Supporting ({{ supporting|length }})</h3>
        {% if supporting %}
          <div class="profiles-container" role="list" aria-label="Supporting">
            {% for profile in supporting %}
              <div class="profile-card" role="listitem">
                <div class="profile-top">
                  <div class="profile-avatar">
                    {% if profile.profile_image %}
                      <img src="{{ profile.profile_image.url }}" alt="{{ profile.user.username }}" style="width:56px;height:56px;border-radius:12px;object-fit:cover" />
                    {% else %}
                      {{ profile.user.username|slice:"0:2"|upper }}
                    {% endif %}
                  </div>
                  <div class="profile-meta">
                    <p class="profile-username"><a class="profile-link" href="{% url 'profile_detail' profile.user.username %}">{{ profile.user.username }}</a></p>
                    <div class="profile-stats">Supporting: <strong>{{ profile.supports_count }}</strong> • Supporters: <strong>{{ profile.supporters_count }}</strong></div>
                  </div>
                </div>

                <div class="profile-actions">
                  {% if request.user.username != profile.user.username %}
                    <form method="post" action="{% url 'toggle_support' profile.user.username %}" style="display:inline" aria-label="Un-support {{ profile.user.username }}">
                      {% csrf_token %}
                      <button type="submit" class="btn btn-primary" aria-pressed="true">Un-support</button>
                    </form>
                  {% else %}
                    <a href="{% url 'profile_detail' profile.user.username %}" class="btn btn-ghost">View</a>
                  {% endif %}
                </div>
              </div>
            {% endfor %}
          </div>
        {% else %}
          <div class="empty-state">You&apos;re not supporting anyone yet. Search for people to support and start connecting.</div>
        {% endif %}
      </section>

    </div>
  {% endif %}
</div>
{% endblock %}
'''

path.write_text(new_content, encoding='utf-8')
print('Wrote profile_list.html')
