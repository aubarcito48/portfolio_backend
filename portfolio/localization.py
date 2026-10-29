"""Reviewed content translations, without altering canonical Spanish database values.

Add an entry when changing public text in Admin. Unknown text falls back to its
original value; URLs, slugs, dates, identifiers and publication are never translated.
"""

ENGLISH = {
    'Realicé una pasantía laboral a través del ISPC (Instituto Superior Politécnico de Córdoba) en la DGES (Dirección General de Educación Superior).':
        'Completed a work internship through ISPC (Instituto Superior Politécnico de Córdoba) at DGES (Dirección General de Educación Superior).',
    'Referencia laboral: Gabriel Cámara — virtualdges@gmail.com':
        'Work reference: Gabriel Cámara — virtualdges@gmail.com',
    'Asistente de escritorio con ESP32, avatar animado, control por voz e inteligencia artificial.':
        'Desktop assistant with ESP32, an animated avatar, voice control and artificial intelligence.',
    'Asistente de escritorio con un avatar animado en una pantalla Waveshare ESP32-S3. Combina firmware en C++ y un panel de control en Python para manejar 28 expresiones y 23 animaciones por voz. Integra conversaciones con Groq, respuestas habladas con Dora y comandos para buscar y reproducir videos de YouTube desde la PC.':
        'Desktop assistant with an animated avatar on a Waveshare ESP32-S3 display. It combines C++ firmware and a Python control panel to manage 28 expressions and 23 animations by voice. It integrates conversations with Groq, spoken responses with Dora, and commands to search for and play YouTube videos from the PC.',
    'Proyecto personal · Hardware e IA': 'Personal project · Hardware and AI',
    'Avatar de Aubar Bot en una pantalla Waveshare ESP32-S3':
        'Aubar Bot avatar on a Waveshare ESP32-S3 display',
    'Sistemas embebidos': 'Embedded systems',
    'Full-Stack Developer | Software Development | QA & Testing':
        'Full-Stack Developer | Software Development | QA & Testing',
    'Soy desarrollador de software de Córdoba, Argentina, y actualmente curso la Tecnicatura Superior en Desarrollo de Software en el Instituto Superior Politécnico de Córdoba (ISPC).':
        'I am a software developer from Córdoba, Argentina, currently studying for a Higher Technical Degree in Software Development at Instituto Superior Politécnico de Córdoba (ISPC).',
    'Me interesa construir aplicaciones web, resolver problemas técnicos, integrar APIs y profundizar en la calidad del software y las pruebas automatizadas. Mi recorrido incluye tecnologías frontend y backend, desarrollo con WordPress y soporte técnico informático.':
        'I am interested in building web applications, solving technical problems, integrating APIs, and developing my knowledge of software quality and automated testing. My background includes frontend and backend technologies, WordPress development, and IT technical support.',
    'Hoy estoy enfocado en seguir creciendo como desarrollador y contribuir a proyectos reales.':
        'I am currently focused on continuing to grow as a developer and contributing to real projects.',
    'Pasante de desarrollo web': 'Web Development Intern',
    'Trabajé con WordPress en un entorno profesional.':
        'Worked with WordPress in a professional environment.',
    'Adquirí experiencia práctica en el desarrollo y mantenimiento de sitios web.':
        'Gained practical experience in website development and maintenance.',
    'Desarrollador full stack independiente': 'Freelance Full-Stack Developer',
    'Desarrollo aplicaciones web y funcionalidades de frontend y backend.':
        'Develop web applications and frontend and backend functionality.',
    'Integro APIs y trabajo con bases de datos.': 'Integrate APIs and work with databases.',
    'Utilizo herramientas de control de versiones y desarrollo colaborativo.':
        'Use version control and collaborative development tools.',
    'Soporte técnico informático': 'IT Technical Support',
    'Participé a través del programa Empleo +26.':
        'Participated through the Empleo +26 program.',
    'Referencia laboral: Mariela Selim — administracion@sanatoriofrances.com.ar':
        'Work reference: Mariela Selim — administracion@sanatoriofrances.com.ar',
    'Brindé soporte técnico en un entorno organizacional.':
        'Provided technical support in an organizational environment.',
    'Colaboré en el diagnóstico y la resolución de problemas informáticos.':
        'Assisted with troubleshooting and resolving IT-related issues.',
    'Tecnicatura Superior en Desarrollo de Software': 'Higher Technical Degree in Software Development',
    'Bases de datos y herramientas': 'Databases and tools',
    'Calidad de software': 'Software quality',
    'Proyecto en equipo': 'Team project',
    'Pasantía · Proyecto en equipo': 'Internship · Team project',
    'Plataforma de libros y ebooks desarrollada por el equipo ISPC / ProCoders.':
        'Book and ebook platform developed by the ISPC / ProCoders team.',
    'Plataforma de libros y ebooks desarrollada como parte del equipo ISPC / ProCoders. El proyecto integra trabajo de frontend y backend, APIs, autenticación y funcionalidades asistidas por inteligencia artificial.':
        'Book and ebook platform developed as part of the ISPC / ProCoders team. The project combines frontend and backend development, APIs, authentication, and AI-assisted features.',
    'Página de inicio de PintaEbook con su presentación y navegación':
        'PintaEbook home page with its introduction and navigation',
    'Actualización y reorganización del sitio institucional de la DGES.':
        'Update and reorganization of the DGES institutional website.',
    'Proyecto de actualización y reorganización del sitio institucional de la DGES, orientado a mejorar el acceso a la información, la experiencia de navegación y la adaptación a distintos dispositivos.':
        'Project to update and reorganize the DGES institutional website, improving access to information, navigation, and responsiveness across devices.',
    'Página de inicio del sitio institucional de la Dirección General de Educación Superior':
        'Home page of the Dirección General de Educación Superior institutional website',
    'Ver demo': 'View demo', 'Ver sitio': 'View website', 'Repositorio': 'Repository',
    'Método no permitido.': 'Method not allowed.',
    'page_size debe ser un entero mayor que cero.': 'page_size must be an integer greater than zero.',
    'La página solicitada no existe.': 'The requested page does not exist.',
    'No hay un perfil publicado.': 'No profile has been published.',
    'No se encontró el proyecto publicado.': 'The published project was not found.',
    'No se encontró el recurso solicitado.': 'The requested resource was not found.',
}

# Titles of people, institutions and products retain their official names.
SPANISH = {
    'Full-Stack Developer | Software Development | QA & Testing':
        'Desarrollador full stack | Desarrollo de software | Calidad y pruebas',
    'Junior Full Stack Developer': 'Desarrollador full stack junior',
}

TEXT_FIELDS = frozenset({
    'name', 'specialty', 'biography', 'location', 'title', 'description',
    'summary', 'type', 'imageAlt', 'label', 'detail',
})


def translate_text(value, language):
    catalog = ENGLISH if language == 'en' else SPANISH
    if value in catalog:
        return catalog[value]
    # Preserve paragraph and line breaks in biography and experience descriptions.
    return '\n'.join(catalog.get(line, line) for line in value.split('\n'))


def localize_payload(value, language):
    if isinstance(value, list):
        return [localize_payload(item, language) for item in value]
    if isinstance(value, dict):
        return {
            key: translate_text(item, language)
            if key in TEXT_FIELDS and isinstance(item, str)
            else localize_payload(item, language)
            for key, item in value.items()
        }
    return value
