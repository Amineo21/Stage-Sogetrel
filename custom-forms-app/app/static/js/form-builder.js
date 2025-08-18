$(document).ready(() => {
  const $ = window.$ // Declare the $ variable
  const formFieldsContainer = $("#formFieldsContainer")
  const noFieldsMessage = $("#noFieldsMessage")
  let fields = [] // Tableau pour stocker la structure des champs
  const EXISTING_FORM_DATA = window.EXISTING_FORM_DATA // Declare the EXISTING_FORM_DATA variable
  const FORM_ID = window.FORM_ID // Declare the FORM_ID variable

  // Charger les champs existants si disponibles
  if (typeof EXISTING_FORM_DATA !== "undefined" && EXISTING_FORM_DATA.length > 0) {
    fields = EXISTING_FORM_DATA
    renderFields()
  } else {
    noFieldsMessage.show()
  }

  // Rendre les champs dans le conteneur
  function renderFields() {
    formFieldsContainer.empty()
    if (fields.length === 0) {
      noFieldsMessage.show()
      return
    }
    noFieldsMessage.hide()

    fields.forEach((field, index) => {
      const fieldHtml = createFieldHtml(field, index)
      formFieldsContainer.append(fieldHtml)
    })

    // Rendre les champs sortables
    formFieldsContainer.sortable({
      handle: ".card-header", // Poignée de déplacement
      axis: "y",
      update: function (event, ui) {
        const newOrder = $(this).sortable("toArray", { attribute: "data-field-id" })
        // Reconstruire le tableau 'fields' selon le nouvel ordre
        const reorderedFields = []
        newOrder.forEach((id) => {
          const originalField = fields.find((f) => f.id === id)
          if (originalField) {
            reorderedFields.push(originalField)
          }
        })
        fields = reorderedFields
        // Pas besoin de re-render ici, l'ordre visuel est déjà mis à jour par sortable
      },
    })
  }

  // Créer le HTML pour un champ donné
  function createFieldHtml(field, index) {
    let optionsHtml = ""
    let choicesHtml = ""

    if (field.type === "radio" || field.type === "select") {
      field.choices.forEach((choice, cIndex) => {
        choicesHtml += `
                    <div class="choice-item" data-choice-index="${cIndex}">
                        <input type="text" class="form-control form-control-sm mb-1" value="${choice.label}" data-choice-property="label" placeholder="Label">
                        <input type="text" class="form-control form-control-sm mb-1" value="${choice.value}" data-choice-property="value" placeholder="Value">
                        <button type="button" class="btn btn-danger btn-sm remove-choice-btn"><i class="fas fa-minus"></i></button>
                    </div>
                `
      })
      optionsHtml += `
                <div class="field-options mt-3">
                    <h6>Options de choix:</h6>
                    <div class="choices-container">
                        ${choicesHtml}
                    </div>
                    <button type="button" class="btn btn-success btn-sm add-choice-btn"><i class="fas fa-plus"></i> Ajouter un choix</button>
                </div>
            `
    } else if (field.type === "checkbox") {
      optionsHtml += `
                <div class="field-options mt-3">
                    <div class="mb-2">
                        <label class="form-label">Label de la case à cocher:</label>
                        <input type="text" class="form-control form-control-sm" value="${field.checkbox_label || ""}" data-field-property="checkbox_label" placeholder="Ex: J'accepte les termes">
                    </div>
                </div>
            `
    } else if (field.type === "file") {
      const allowedExtensions = (field.allowed_extensions || []).join(", ")
      optionsHtml += `
                <div class="field-options mt-3">
                    <div class="mb-2">
                        <label class="form-label">Extensions autorisées (séparées par des virgules):</label>
                        <input type="text" class="form-control form-control-sm" value="${allowedExtensions}" data-field-property="allowed_extensions" placeholder="Ex: jpg, png, pdf">
                    </div>
                </div>
            `
    } else if (field.type === "email") {
      optionsHtml += `
                <div class="field-options mt-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="is_recipient_email_${field.id}" data-field-property="is_recipient_email" ${field.is_recipient_email ? "checked" : ""}>
                        <label class="form-check-label" for="is_recipient_email_${field.id}">
                            Utiliser comme email de destinataire pour les notifications
                        </label>
                    </div>
                </div>
            `
    }

    return `
            <div class="card form-builder-field mb-3" data-field-id="${field.id}" data-field-index="${index}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0"><i class="fas fa-arrows-alt me-2"></i>${field.label || "Nouveau champ"} (${field.type})</h6>
                    <div class="field-actions">
                        <button type="button" class="btn btn-sm btn-outline-secondary toggle-options-btn" title="Options"><i class="fas fa-cog"></i></button>
                        <button type="button" class="btn btn-sm btn-danger remove-field-btn" title="Supprimer"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
                <div class="card-body field-settings" style="display: none;">
                    <div class="mb-2">
                        <label class="form-label">Label:</label>
                        <input type="text" class="form-control form-control-sm" value="${field.label}" data-field-property="label" placeholder="Label du champ">
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Nom (unique, pour la base de données):</label>
                        <input type="text" class="form-control form-control-sm" value="${field.name}" data-field-property="name" placeholder="Nom unique (ex: prenom_utilisateur)">
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Placeholder (optionnel):</label>
                        <input type="text" class="form-control form-control-sm" value="${field.placeholder || ""}" data-field-property="placeholder" placeholder="Texte d'exemple dans le champ">
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Texte d'aide (optionnel):</label>
                        <input type="text" class="form-control form-control-sm" value="${field.help_text || ""}" data-field-property="help_text" placeholder="Texte d'aide sous le champ">
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="checkbox" id="required_${field.id}" data-field-property="required" ${field.required ? "checked" : ""}>
                        <label class="form-check-label" for="required_${field.id}">
                            Champ requis
                        </label>
                    </div>
                    ${optionsHtml}
                </div>
            </div>
        `
  }

  // Ajouter un nouveau champ
  $(".btn-outline-primary").click(function () {
    const type = $(this).data("field-type")
    const newField = {
      id: "field_" + Date.now(), // ID unique pour le champ
      type: type,
      label: `Nouveau champ ${type}`,
      name: `${type}_${Date.now()}`, // Nom par défaut, à modifier par l'utilisateur
      required: false,
      placeholder: "",
      help_text: "",
    }

    if (type === "radio" || type === "select") {
      newField.choices = [
        { label: "Option 1", value: "option1" },
        { label: "Option 2", value: "option2" },
      ]
    } else if (type === "checkbox") {
      newField.checkbox_label = "Cochez cette case"
    } else if (type === "file") {
      newField.allowed_extensions = ["pdf", "doc", "docx", "jpg", "png"]
    } else if (type === "email") {
      newField.is_recipient_email = false
    }

    fields.push(newField)
    renderFields()
  })

  // Supprimer un champ
  formFieldsContainer.on("click", ".remove-field-btn", function () {
    const fieldElement = $(this).closest(".form-builder-field")
    const fieldId = fieldElement.data("field-id")
    fields = fields.filter((field) => field.id !== fieldId)
    fieldElement.remove()
    if (fields.length === 0) {
      noFieldsMessage.show()
    }
  })

  // Basculer les options d'un champ
  formFieldsContainer.on("click", ".toggle-options-btn", function () {
    $(this).closest(".form-builder-field").find(".field-settings").slideToggle()
  })

  // Mettre à jour les propriétés du champ lors de la saisie
  formFieldsContainer.on("input change", "input[data-field-property], textarea[data-field-property]", function () {
    const fieldElement = $(this).closest(".form-builder-field")
    const fieldId = fieldElement.data("field-id")
    const property = $(this).data("field-property")
    const value = $(this).is(":checkbox") ? $(this).prop("checked") : $(this).val()

    const fieldIndex = fields.findIndex((f) => f.id === fieldId)
    if (fieldIndex !== -1) {
      if (property === "allowed_extensions") {
        fields[fieldIndex][property] = value
          .split(",")
          .map((ext) => ext.trim())
          .filter((ext) => ext !== "")
      } else {
        fields[fieldIndex][property] = value
      }
      // Mettre à jour le label dans le header si c'est le label principal qui change
      if (property === "label") {
        fieldElement
          .find(".card-header h6")
          .html(`<i class="fas fa-arrows-alt me-2"></i>${value} (${fields[fieldIndex].type})`)
      }
    }
  })

  // Ajouter un choix pour radio/select
  formFieldsContainer.on("click", ".add-choice-btn", function () {
    const fieldElement = $(this).closest(".form-builder-field")
    const fieldId = fieldElement.data("field-id")
    const fieldIndex = fields.findIndex((f) => f.id === fieldId)

    if (fieldIndex !== -1) {
      const newChoice = {
        label: `Nouvelle option ${fields[fieldIndex].choices.length + 1}`,
        value: `option${Date.now()}`,
      }
      fields[fieldIndex].choices.push(newChoice)

      const choicesContainer = $(this).siblings(".choices-container")
      const newChoiceHtml = `
                <div class="choice-item" data-choice-index="${fields[fieldIndex].choices.length - 1}">
                    <input type="text" class="form-control form-control-sm mb-1" value="${newChoice.label}" data-choice-property="label" placeholder="Label">
                    <input type="text" class="form-control form-control-sm mb-1" value="${newChoice.value}" data-choice-property="value" placeholder="Value">
                    <button type="button" class="btn btn-danger btn-sm remove-choice-btn"><i class="fas fa-minus"></i></button>
                </div>
            `
      choicesContainer.append(newChoiceHtml)
    }
  })

  // Supprimer un choix pour radio/select
  formFieldsContainer.on("click", ".remove-choice-btn", function () {
    const choiceItem = $(this).closest(".choice-item")
    const fieldElement = $(this).closest(".form-builder-field")
    const fieldId = fieldElement.data("field-id")
    const choiceIndex = choiceItem.data("choice-index")

    const field = fields.find((f) => f.id === fieldId)
    if (field && field.choices) {
      field.choices.splice(choiceIndex, 1)
      // Re-index the remaining choices visually
      choiceItem.siblings().each(function (i) {
        $(this).data("choice-index", i)
      })
      choiceItem.remove()
    }
  })

  // Mettre à jour les propriétés des choix
  formFieldsContainer.on("input", ".choice-item input", function () {
    const choiceItem = $(this).closest(".choice-item")
    const fieldElement = $(this).closest(".form-builder-field")
    const fieldId = fieldElement.data("field-id")
    const choiceIndex = choiceItem.data("choice-index")
    const property = $(this).data("choice-property")
    const value = $(this).val()

    const field = fields.find((f) => f.id === fieldId)
    if (field && field.choices && field.choices[choiceIndex]) {
      field.choices[choiceIndex][property] = value
    }
  })

  // Sauvegarder les champs du formulaire via API
  $("#saveFormFields").click(() => {
    // Valider les noms de champs uniques et non vides
    const fieldNames = new Set()
    let isValid = true
    fields.forEach((field) => {
      if (!field.name || field.name.trim() === "") {
        alert(`Le champ "${field.label}" doit avoir un nom unique et non vide.`)
        isValid = false
        return
      }
      if (fieldNames.has(field.name)) {
        alert(`Le nom de champ "${field.name}" est dupliqué. Les noms de champs doivent être uniques.`)
        isValid = false
        return
      }
      fieldNames.add(field.name)
    })

    if (!isValid) {
      return
    }

    $.ajax({
      url: `/api/forms/${FORM_ID}/save_fields`,
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ form_data: fields }),
      success: (response) => {
        alert(response.message)
      },
      error: (xhr, status, error) => {
        alert("Erreur lors de la sauvegarde des champs: " + (xhr.responseJSON ? xhr.responseJSON.error : error))
        console.error("Erreur de sauvegarde:", xhr.responseText)
      },
    })
  })
})
