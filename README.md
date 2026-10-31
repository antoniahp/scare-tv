# 👻 Scare-TV

Your TV becomes a haunted mirror. A webcam watches and, when a person walks by, the TV possesses their own reflection: black eyes, no face, a girl behind them… and a jump scare with sound.

Everything runs locally: open-weight vision (YOLO11n-pose) for people and faces, and SD-Turbo for the realistic scares.

Built with Django + Django REST Framework, a hexagonal architecture with CQRS, and Poetry.

```bash
poetry install --no-root
python manage.py migrate
```
