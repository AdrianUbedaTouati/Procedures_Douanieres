// Authentication Module - Funciones básicas
(function() {
    'use strict';

    // Initialize on DOM load
    document.addEventListener('DOMContentLoaded', function() {
        initPasswordToggles();
        initPasswordValidation();
    });

    // Password visibility toggle
    function initPasswordToggles() {
        const toggleButtons = document.querySelectorAll('.password-toggle');

        toggleButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const passwordInput = document.getElementById(targetId);
                const icon = document.getElementById(targetId + '-icon');

                if (passwordInput && icon) {
                    if (passwordInput.type === 'password') {
                        passwordInput.type = 'text';
                        icon.classList.remove('bi-eye');
                        icon.classList.add('bi-eye-slash');
                        this.setAttribute('aria-label', 'Ocultar contraseña');
                    } else {
                        passwordInput.type = 'password';
                        icon.classList.remove('bi-eye-slash');
                        icon.classList.add('bi-eye');
                        this.setAttribute('aria-label', 'Mostrar contraseña');
                    }
                }
            });
        });
    }

    // Real-time password validation
    function initPasswordValidation() {
        const passwordInputs = document.querySelectorAll('#password1, #new-password1');

        passwordInputs.forEach(input => {
            // Create validation feedback element if it doesn't exist
            if (input && !input.parentElement.querySelector('.password-validation-feedback')) {
                const feedbackDiv = createPasswordFeedback();
                input.parentElement.parentElement.appendChild(feedbackDiv);

                input.addEventListener('input', function() {
                    updatePasswordFeedback(this.value, feedbackDiv);
                });

                // Show feedback on focus
                input.addEventListener('focus', function() {
                    feedbackDiv.style.display = 'block';
                });
            }
        });
    }

    // Create password validation feedback element
    function createPasswordFeedback() {
        const div = document.createElement('div');
        div.className = 'password-validation-feedback mt-2';
        div.style.display = 'none';
        div.innerHTML = `
            <small class="text-muted">
                <div class="requirement" data-requirement="length">
                    <i class="bi bi-circle"></i> Mínimo 8 caracteres
                </div>
                <div class="requirement" data-requirement="uppercase">
                    <i class="bi bi-circle"></i> Al menos 1 mayúscula
                </div>
                <div class="requirement" data-requirement="special">
                    <i class="bi bi-circle"></i> Al menos 1 carácter especial (!@#$%^&*(),.?":{}|<>)
                </div>
            </small>
        `;
        return div;
    }

    // Update password validation feedback
    function updatePasswordFeedback(password, feedbackDiv) {
        const requirements = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };

        Object.keys(requirements).forEach(key => {
            const element = feedbackDiv.querySelector(`[data-requirement="${key}"]`);
            const icon = element.querySelector('i');

            if (requirements[key]) {
                element.classList.remove('text-danger');
                element.classList.add('text-success');
                icon.classList.remove('bi-circle', 'bi-x-circle');
                icon.classList.add('bi-check-circle');
            } else {
                element.classList.remove('text-success');
                element.classList.add('text-danger');
                icon.classList.remove('bi-circle', 'bi-check-circle');
                icon.classList.add('bi-x-circle');
            }
        });

        const allMet = Object.values(requirements).every(req => req === true);
        return allMet;
    }

})();