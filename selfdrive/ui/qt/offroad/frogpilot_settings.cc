#include <QHBoxLayout>
#include <QWidget>
#include <tuple>
#include <vector>

#include "common/params.h"
#include "selfdrive/ui/qt/offroad/frogpilot_settings.h"
#include "selfdrive/ui/qt/widgets/input.h"
#include "selfdrive/ui/ui.h"

FrogPilotPanel::FrogPilotPanel(QWidget *parent) : QWidget(parent) {
  mainLayout = new QVBoxLayout(this);

  const std::vector<std::tuple<QString, QString, QString, QString>> toggles = {
  };

  for (const auto &[key, label, desc, icon] : toggles) {
    ParamControl *control = createParamControl(key, label, desc, icon, this);
    if (key == "") {
      });
    } else {
      mainLayout->addWidget(control);
      if (key != std::get<0>(toggles.back())) mainLayout->addWidget(horizontal_line());
    }
  }
  setInitialToggleStates();
}

ParamControl *FrogPilotPanel::createParamControl(const QString &key, const QString &label, const QString &desc, const QString &icon, QWidget *parent) {
  ParamControl *control = new ParamControl(key, label, desc, icon);
  connect(control, &ParamControl::toggleFlipped, [=](bool state) {
    if (ConfirmationDialog::toggle("Reboot required to take effect.", "Reboot Now", parent)) {
      Hardware::reboot();
    }
    auto it = childControls.find(key.toStdString());
    if (it != childControls.end()) {
      for (QWidget *widget : it->second) {
        widget->setVisible(state);
      }
    }
  });
  return control;
}

QWidget *FrogPilotPanel::createDualParamControl(ParamValueControl *control1, ParamValueControl *control2) {
  QWidget *mainControl = new QWidget(this);
  QHBoxLayout *layout = new QHBoxLayout();
  layout->addWidget(control1);
  layout->addStretch();
  layout->addWidget(control2);
  mainControl->setLayout(layout);
  return mainControl;
}

QWidget *FrogPilotPanel::addSubControls(const QString &parentKey, QVBoxLayout *layout, const std::vector<std::tuple<QString, QString, QString>> &controls) {
  QWidget *mainControl = new QWidget(this);
  mainControl->setLayout(layout);
  mainLayout->addWidget(mainControl);
  mainControl->setVisible(Params().getBool(parentKey.toStdString()));
  for (const auto &[key, label, desc] : controls) addControl(key, "   " + label, desc, layout);
  return mainControl;
}

void FrogPilotPanel::addControl(const QString &key, const QString &label, const QString &desc, QVBoxLayout *layout, const QString &icon) {
  layout->addWidget(createParamControl(key, label, desc, icon, this));
  layout->addWidget(horizontal_line());
}

void FrogPilotPanel::createSubControl(const QString &key, const QString &label, const QString &desc, const QString &icon, const std::vector<QWidget*> &subControls, const std::vector<std::tuple<QString, QString, QString>> &additionalControls) {
  ParamControl *control = createParamControl(key, label, desc, icon, this);
  mainLayout->addWidget(control);
  mainLayout->addWidget(horizontal_line());
  QVBoxLayout *subControlLayout = new QVBoxLayout();
  for (QWidget *subControl : subControls) {
    subControlLayout->addWidget(subControl);
    subControlLayout->addWidget(horizontal_line());
  }
  QWidget *mainControl = addSubControls(key, subControlLayout, additionalControls);
  connect(control, &ParamControl::toggleFlipped, [=](bool state) { mainControl->setVisible(state); });
}

void FrogPilotPanel::createSubButtonControl(const QString &parentKey, const std::vector<QPair<QString, QString>> &buttonKeys, QVBoxLayout *subControlLayout) {
  QHBoxLayout *buttonsLayout = new QHBoxLayout();
  QWidget *line = horizontal_line();
  buttonsLayout->addStretch();
  for (const auto &[key, label] : buttonKeys) {
    FrogPilotButtonParamControl* button = new FrogPilotButtonParamControl(key, label);
    mainLayout->addWidget(button);
    buttonsLayout->addWidget(button);
    buttonsLayout->addStretch();
    button->setVisible(Params().getBool(parentKey.toStdString()));
    childControls[parentKey.toStdString()].push_back(button);
  }
  subControlLayout->addLayout(buttonsLayout);
  line = horizontal_line();
  mainLayout->addWidget(line);
  childControls[parentKey.toStdString()].push_back(line);
}

void FrogPilotPanel::setInitialToggleStates() {
  for (const auto& [key, controlSet] : childControls) {
    bool state = Params().getBool(key);
    for (QWidget *widget : controlSet) {
      widget->setVisible(state);
    }
  }
}
