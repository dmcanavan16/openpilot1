#pragma once

#include <QWidget>
#include <QVBoxLayout>

#include "selfdrive/ui/qt/widgets/controls.h"

class FrogPilotPanel : public QWidget {
  Q_OBJECT

public:
  explicit FrogPilotPanel(QWidget *parent = nullptr);

private:
  QVBoxLayout *mainLayout;

  ParamControl *createParamControl(const QString &key, const QString &label, const QString &desc, const QString &icon, QWidget *parent);
  void addControl(const QString &key, const QString &label, const QString &desc, QVBoxLayout *layout, const QString &icon = "../assets/offroad/icon_blank.png", bool addHorizontalLine = true);
  QWidget *addSubControls(const QString &parentKey, QVBoxLayout *layout, const std::vector<std::tuple<QString, QString, QString>> &controls);
  void createSubControl(const QString &key, const QString &label, const QString &desc, const QString &icon, const std::vector<QWidget*> &subControls, const std::vector<std::tuple<QString, QString, QString>> &additionalControls = {});
};

class ParamValueControl : public AbstractControl {
protected:
  ParamValueControl(const QString& name, const QString& description, const QString& iconPath) : AbstractControl(name, description, iconPath) {
    label.setAlignment(Qt::AlignVCenter | Qt::AlignRight);
    label.setStyleSheet("color: #e0e879");
    setupButton(btnminus, "-", -1);
    setupButton(btnplus, "+", 1);
    hlayout->addWidget(&label);
    hlayout->addWidget(&btnminus);
    hlayout->addWidget(&btnplus);
  }

  void setupButton(QPushButton &btn, const QString &text, int delta) {
    btn.setStyleSheet("QPushButton { background-color: #393939; color: #E4E4E4; border-radius: 50px; font: 500 35px; padding: 0; } QPushButton:pressed { background-color: #4a4a4a; color: #E4E4E4; }");
    btn.setText(text);
    btn.setFixedSize(150, 100);
    btn.setAutoRepeat(true);
    btn.setAutoRepeatInterval(150);
    connect(&btn, &QPushButton::clicked, [this, delta]() { updateValue(delta); });
  }

  QPushButton btnminus, btnplus;
  QLabel label;
  Params params;

  virtual void updateValue(int delta) = 0;
  virtual void refresh() = 0;
};

#define ParamController(className, paramName, labelText, descText, iconPath, getValueStrFunc, newValueFunc) \
class className : public ParamValueControl { \
  Q_OBJECT \
public: \
  className() : ParamValueControl(labelText, descText, iconPath) { refresh(); } \
private: \
  void refresh() override { label.setText(getValueStr()); } \
  void updateValue(int delta) override { \
    int value = QString::fromStdString(params.get(paramName)).toInt(); \
    value = newValue(value + delta); \
    params.put(paramName, QString::number(value).toStdString()); \
    refresh(); \
  } \
  QString getValueStr() { getValueStrFunc } \
  int newValue(int v) { newValueFunc } \
};

ParamController(ScreenBrightness, "ScreenBrightness", "Screen Brightness", "Choose a custom screen brightness level or use the default 'Auto' brightness setting.", "../assets/offroad/icon_light.png",
  int brightness = QString::fromStdString(params.get("ScreenBrightness")).toInt();
  return brightness > 100 ? "Auto" : brightness == 0 ? "Screen Off" : QString::number(brightness) + "%";,
  return std::clamp(v, 0, 101);
)
