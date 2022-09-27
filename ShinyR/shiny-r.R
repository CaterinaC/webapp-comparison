
library(dplyr)
library(shiny)
library(shinyWidgets)
library(plotly)
library(data.table)
library(magrittr)
library(prophet)

dt <- fread("/home/caterina/Documents/TalksJune2020Onwards/ShinyVsPythonCompetitors/code/ShinyR/data/NEED_data_explorer_2021.csv",
            na.strings = "n/a")

REGIONS <- c("North East", 
             "North West", 
             "Yorks & Humber",
             "East Midlands",
             "West Midlands", 
             "East of England", 
             "London", 
             "South East",
             "South West", 
             "Wales")

PERIODS <- c("Pre 1919",
             "1919-44",
             "1945-64",
             "1965-82",
             "1983-92",
             "1993-99",
             "Post 1999")

GAS_DIMS <- grep("Gas Median", names(dt), value =  TRUE)
ELEC_DIMS <- grep("Elec Median", names(dt), value =  TRUE)






ui <- pageWithSidebar(
  headerPanel('Test app'),
  sidebarPanel(
    
    pickerInput(inputId = "energy_type", 
                label = "Energy type:", 
                choices = c("Electricity", "Gas"), 
                multiple = FALSE, 
                selected = "Electricity"),
    
    pickerInput(inputId = "Id008", 
                label = "Select region:", 
                choices = REGIONS, 
                multiple = FALSE, 
                selected = REGIONS[1])
    
  ),
  mainPanel(
    plotlyOutput('plot1', height = "800px")
  )
)



server <- function(input, output, session) {
  
  
  selectedData <- reactive({
    
    if (input$energy_type == "Gas") {
      dt_chunk <- dt[ `Attribute 1` %in% input$Id008 & `Attribute 2` %in% PERIODS, 
                      c("Attribute 1",
                        "Attribute 2",
                        GAS_DIMS), 
                      with = FALSE]
      dt_chunk <- melt(dt_chunk, measure.vars = sort(GAS_DIMS))
      
      dt_chunk[ , variable := gsub("Gas Median ", "", variable) %>% as.numeric()]
      
      dt_chunk[ , value := as.numeric(value)]
      
    } else if (input$energy_type == "Electricity") {
      dt_chunk <- dt[ `Attribute 1` %in% input$Id008 & `Attribute 2` %in% PERIODS, 
                      c("Attribute 1",
                        "Attribute 2",
                        ELEC_DIMS), 
                      with = FALSE]
      
      dt_chunk <- melt(dt_chunk, measure.vars = sort(ELEC_DIMS))
      
      dt_chunk[ , variable := gsub("Elec Median ", "", variable) %>% as.numeric()]
      
      dt_chunk[ , value := as.numeric(value)]
    }

    return(dt_chunk)
  })
  
  
  output$plot1 <- renderPlotly({
    
    
    s_data_copy <- selectedData()
    s_data_copy[ , date := as.POSIXct(as.Date(paste(variable, "01", "01", sep = "-")))]
    
    
    forecast_collector <- data.table()
    for (build_age in unique(s_data_copy$`Attribute 2`)) {
      
      s_data_copy_subset <- s_data_copy[ `Attribute 2` == build_age, ]
      history <- data.frame(ds = s_data_copy_subset$date,
                            y = s_data_copy_subset$value)
      m <- prophet(history)
      future <- make_future_dataframe(m, periods = 2, freq='year')
      forecast <- predict(m, future)
      
      # TOOD: ADD 
      
      s_data_copy_subset <- merge(s_data_copy_subset,
                                  forecast[ , c("ds", "yhat", "yhat_lower", "yhat_upper")],
                                  by.x = "date",
                                  by.y = "ds",
                                  all = TRUE)
      
      s_data_copy_subset[ is.na(`Attribute 1`), "Attribute 1"] <- unique(s_data_copy_subset$`Attribute 1`) %>% na.exclude()
      s_data_copy_subset[ is.na(`Attribute 2`), "Attribute 2"] <- unique(s_data_copy_subset$`Attribute 2`) %>% na.exclude()
      
      # Now add to full set:
      forecast_collector <- rbind(forecast_collector,
                                  s_data_copy_subset)
    }
    
    
    forecast_collector <- melt(forecast_collector, 
                               id.vars = c("date", "Attribute 1", "Attribute 2"), 
                               measure.vars = c("value", "yhat"))

    
    # browser()


    forecast_collector[ , `Attribute 2` := recode(`Attribute 2`, 
                                                  `Pre 1919` = "6. Oldest buildings: Pre 1919",
                                                  `1919-44` = "5. Older buildings: 1919-44", 
                                                  `1945-64` = "4. Older buildings: 1945-64",
                                                  `1965-82` = "3. Older buildings: 1965-82",
                                                  `1983-92` = "2. Recent buildings: 1983-92",
                                                  `1993-99` = "1. Recent buildings: 1993-99",
                                                  `Post 1999` = "0. New buildings: Post 1999")]
    forecast_collector[ , `Attribute 2` := factor(`Attribute 2`,
                                                  levels = sort(unique(`Attribute 2`)),
                                                  ordered = TRUE)]
    forecast_collector[ , variable := recode(variable, 
                                                  `value` = "(actuals)",
                                                  `yhat` = "(predicted)")]
    
    # browser()
    plot_ly(data = forecast_collector, 
            x = ~date,
            y = ~value,
            legendgroup = ~variable,
            linetype = ~variable,
            color = ~`Attribute 2`) %>%
      add_lines(
                type = 'scatter', 
                mode = "lines+markers",
                line = list(width = 4)
                ) %>%
      layout(title = 'Forecasted vs actual energy usage at yearly level',
             legend = list(orientation = "h",   # show entries horizontally
                           xanchor = "left",  # use center of legend as anchor
                           y = 0.7,
                           x = 1
                           ),
             xaxis = list(title = 'Year'),
             yaxis = list(title = 'Median energy usage')
             )
    
  })
  
}


# Return a Shiny app object
shinyApp(ui = ui, server = server)

