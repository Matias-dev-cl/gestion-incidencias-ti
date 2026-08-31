# Deploy en AWS

Notas de la puesta en producción. La aplicación está preparada para correr detrás de un proxy con HTTPS, sirviendo sus propios estáticos con WhiteNoise y con la base en un servicio gestionado.

## Qué ya está resuelto en el código

- **Configuración por variables de entorno.** `config/settings.py` no tiene nada codificado: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `DATABASE_URL` se leen del entorno.
- **Estáticos.** WhiteNoise con `CompressedManifestStaticFilesStorage`: los archivos se sirven comprimidos y con hash en el nombre, sin necesitar CloudFront ni un bucket para que el sitio funcione.
- **Endurecimiento con `DEBUG=False`.** Se activan solos: redirección a HTTPS, HSTS, cookies `Secure` y `SECURE_PROXY_SSL_HEADER` para leer bien el esquema detrás del balanceador.
- **`Procfile`.** `release` corre las migraciones antes de publicar la versión; `web` levanta Gunicorn.

## Variables de entorno en producción

```
SECRET_KEY=<clave larga y aleatoria, distinta a la de desarrollo>
DEBUG=False
ALLOWED_HOSTS=<dominio o DNS del entorno>
CSRF_TRUSTED_ORIGINS=https://<dominio>
DATABASE_URL=postgres://<usuario>:<clave>@<endpoint-rds>:5432/<base>
```

`SECRET_KEY` y las credenciales de la base van en AWS Secrets Manager o en las propiedades del entorno, nunca en el repositorio.

## Pasos

1. **Base de datos.** Instancia PostgreSQL en Amazon RDS, en la misma VPC que la aplicación, sin acceso público. El grupo de seguridad de RDS acepta el puerto 5432 solo desde el grupo de seguridad de la aplicación.
2. **Aplicación.** Elastic Beanstalk (plataforma Python) o App Runner, tomando el `Procfile`. Ambos ejecutan `pip install -r requirements.txt` en el despliegue.
3. **Estáticos.** `python manage.py collectstatic --noinput` en el build. El CSS de Tailwind ya viene compilado y versionado, así que el servidor de producción no necesita Node.
4. **Migraciones.** Las corre el paso `release` del `Procfile`.
5. **Primer usuario.** `python manage.py createsuperuser` una vez, por consola en la instancia.
6. **HTTPS.** Certificado en AWS Certificate Manager, asociado al balanceador. Recién con el dominio apuntando se completan `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.

## Checklist antes de publicar

- [ ] `DEBUG=False` y `SECRET_KEY` propia del entorno.
- [ ] `python manage.py check --deploy` sin advertencias relevantes.
- [ ] `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con el dominio real.
- [ ] RDS sin acceso público y con backups automáticos activos.
- [ ] `collectstatic` ejecutado y estáticos respondiendo con 200.
- [ ] Usuario administrador creado y la carga de demo **no** ejecutada en producción.
